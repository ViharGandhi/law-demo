"""
Two-Step RAG Chatbot for Law Firm
=================================
Step 1: User question + index.json → AI picks the relevant file(s)
Step 2: File content + question → AI answers based on the content

Usage:
    python bot.py

Requires:
    pip install openai
"""

import os
import json
from openai import OpenAI

# ─── Configuration ───────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "information")
INDEX_FILE = os.path.join(DATA_DIR, "index.json")
MINI_CONTEXT_FILE = os.path.join(os.path.dirname(__file__), "mini-context.md")

# Put your OpenAI API key here
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    # Small fallback for local dev if .env exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    except ImportError:
        pass

if not OPENAI_API_KEY:
    # Final check: Fail gracefully if no key is provided
    OPENAI_API_KEY = "" # Set in Vercel or a local .env file

client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-5-nano"


# ─── Load Index ──────────────────────────────────────────────────────────────
def load_index():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── Load Mini Context ───────────────────────────────────────────────────────
def load_mini_context():
    """Load the mini-context.md quick-overview document."""
    if os.path.exists(MINI_CONTEXT_FILE):
        with open(MINI_CONTEXT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return ""


# ─── Helper: Convert frontend history to OpenAI messages ─────────────────────
def _build_history(history: list[dict]) -> list[dict]:
    """
    Convert [{role: 'user'|'bot', content: '...'}] from the frontend
    into OpenAI-compatible [{role: 'user'|'assistant', content: '...'}].
    Keep only the last 10 exchanges to stay within context limits.
    """
    messages = []
    for msg in history[-10:]:
        role = "assistant" if msg.get("role") == "bot" else "user"
        messages.append({"role": role, "content": msg.get("content", "")})
    return messages


# ─── Step 0: Try answering from mini-context.md first ────────────────────────
def try_mini_context(question: str, mini_context: str, firm_name: str, history: list[dict] = None) -> str | None:
    """
    Attempt to answer the question using only mini-context.md.
    Returns the answer string if the AI can answer confidently,
    or None if it needs more detailed files.
    """
    if not mini_context:
        return None

    system_prompt = f"""You are a warm, caring assistant for {firm_name}.
You have been given a quick-overview document about the firm.

TONE & STYLE:
- Speak like a kind, knowledgeable friend who works at a family law firm.
- Be empathetic — the person reaching out may be going through one of the hardest times of their life.
- Keep things conversational and reassuring, not robotic or overly formal.
- Use simple, clear language. Avoid excessive legal jargon.

RULES:
- If the user's question can be FULLY and CONFIDENTLY answered using ONLY the overview below, answer it directly.
- If the question is a greeting or general chat, respond warmly and let them know you're here to help with anything about the firm.
- If the overview does NOT contain enough detail to answer properly, respond with EXACTLY the word: NEED_MORE_INFO
- Do NOT guess or make up information beyond what is provided.

FIRM OVERVIEW:
{mini_context}"""

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(_build_history(history))
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )

    answer = response.choices[0].message.content.strip()

    # If the AI says it needs more info, return None to trigger the full chain
    if answer == "NEED_MORE_INFO" or answer.startswith("NEED_MORE_INFO"):
        return None

    return answer


# ─── Step 1: Ask AI which file(s) to look at ────────────────────────────────
def pick_files(question: str, index: dict) -> list[str]:
    """
    Send the question + index.json to AI.
    AI returns the file path(s) most relevant to the question.
    """
    sections_summary = json.dumps(index["sections"], indent=2)

    system_prompt = """You are a file router for a law firm chatbot. 
Given a user's question and a list of available document sections, 
pick the file(s) most likely to contain the answer.

RULES:
- Return ONLY a JSON array of file paths, nothing else.
- Pick 1-3 most relevant files. Prefer fewer files.
- If the question is a greeting or general chat, return: ["NONE"]
- Do NOT explain your choice."""

    user_prompt = f"""AVAILABLE SECTIONS:
{sections_summary}

USER QUESTION: {question}

Respond with ONLY a JSON array of "path" values, e.g. ["contact.md", "about.md"]"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    text = response.choices[0].message.content.strip()

    # Clean markdown fences if AI wraps it
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        files = json.loads(text)
        if isinstance(files, list):
            return files
    except json.JSONDecodeError:
        pass

    return ["NONE"]


# ─── Step 2: Read file + answer question ─────────────────────────────────────
def answer_question(question: str, file_paths: list[str], index: dict, history: list[dict] = None) -> str:
    """
    Read the content of the selected file(s) and ask AI to answer
    the question based on that content.
    """
    firm_name = index.get("firm_name", "our firm")

    if not file_paths or file_paths == ["NONE"]:
        system_prompt = f"""You are a warm, caring assistant for {firm_name}. 
You're here to help people who may be dealing with difficult family situations.

TONE & STYLE:
- Speak like a kind, knowledgeable friend — empathetic, patient, and reassuring.
- Keep things conversational. Avoid sounding robotic or overly formal.
- If they're greeting you, greet them back warmly and let them know you're here to help with any questions about the firm.
- If the question is clearly unrelated to family law or the firm, gently let them know you can only help with questions related to {firm_name}."""

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(_build_history(history))
        messages.append({"role": "user", "content": question})

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
        )
        return response.choices[0].message.content.strip()

    # Load content from the selected files
    base_dir = os.path.dirname(os.path.abspath(__file__))
    context_parts = []
    for fp in file_paths:
        full_path = os.path.join(base_dir, fp)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            context_parts.append(f"--- FILE: {fp} ---\n{content}\n")
        else:
            context_parts.append(f"--- FILE: {fp} --- (not found)\n")

    context = "\n".join(context_parts)

    system_prompt = f"""You are a warm, caring assistant for {firm_name}.
Answer the user's question based ONLY on the information provided below.
If the answer is not in the provided content, let them know kindly and suggest they reach out to the firm directly — they'd be happy to help.

TONE & STYLE:
- Speak like a kind, knowledgeable friend who works at a family law firm.
- Be empathetic — the person may be going through a really tough time. Acknowledge that when it feels right.
- Keep things conversational, clear, and reassuring. Avoid sounding like a robot.
- Use bullet points when listing multiple items, but keep it warm.

FIRM INFORMATION:
{context}"""

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(_build_history(history))
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )
    return response.choices[0].message.content.strip()


# ─── Main Chat Loop ─────────────────────────────────────────────────────────
def main():
    index = load_index()
    firm = index.get("firm_name", "Law Firm")
    mini_context = load_mini_context()

    print(f"\n{'='*60}")
    print(f"  💬 {firm} — AI Chat Assistant")
    print(f"  Type 'quit' or 'exit' to end the conversation")
    print(f"{'='*60}\n")

    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() in ("quit", "exit", "bye", "q"):
            print("\nBot: Thank you for reaching out! Have a great day. 👋\n")
            break

        print("  ⏳ Thinking...")

        # Step 0: Try answering from mini-context.md first
        quick_answer = try_mini_context(question, mini_context, firm)
        if quick_answer is not None:
            print("  ✅ Answered from quick overview")
            print(f"\nBot: {quick_answer}\n")
            continue

        # Step 1: Mini-context wasn't enough — pick the right file(s)
        print("  🔍 Need more detail, searching files...")
        selected_files = pick_files(question, index)
        print(f"  📂 Looking at: {selected_files}")

        # Step 2: Read file content + answer
        answer = answer_question(question, selected_files, index)
        print(f"\nBot: {answer}\n")


if __name__ == "__main__":
    main()
