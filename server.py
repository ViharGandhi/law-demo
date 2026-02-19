"""
Flask server that wraps bot.py and serves the website + chat API.

Usage:
    pip install flask openai
    python server.py

Then open http://localhost:5000 in your browser.
"""

import os
import json
import time
import traceback
from flask import Flask, request, jsonify, send_from_directory
from bot import pick_files, answer_question, load_index, try_mini_context, load_mini_context

# ─── Flask App ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR)

# Load the index once at startup
index = load_index()
mini_context = load_mini_context()


# ─── Rate Limiter (IP-based, in-memory) ──────────────────────────────────────
class RateLimiter:
    """Simple sliding-window rate limiter. No external dependencies."""

    def __init__(self, per_minute=15, per_hour=60):
        self.per_minute = per_minute
        self.per_hour = per_hour
        self._hits = {}  # ip -> list of timestamps

    def _cleanup(self, ip, now):
        """Remove timestamps older than 1 hour."""
        self._hits[ip] = [t for t in self._hits.get(ip, []) if now - t < 3600]

    def is_allowed(self, ip: str) -> tuple[bool, str]:
        now = time.time()
        self._cleanup(ip, now)
        hits = self._hits.get(ip, [])

        # Check per-minute limit
        recent_minute = [t for t in hits if now - t < 60]
        if len(recent_minute) >= self.per_minute:
            return False, "You're sending messages too quickly. Please wait a moment before trying again."

        # Check per-hour limit
        if len(hits) >= self.per_hour:
            return False, "You've reached the maximum number of messages for this session. Please try again later."

        # Record this hit
        self._hits.setdefault(ip, []).append(now)
        return True, ""


rate_limiter = RateLimiter(per_minute=15, per_hour=60)


# ─── Serve the website ───────────────────────────────────────────────────────
@app.route("/")
def serve_index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(BASE_DIR, filename)


# ─── Chat API endpoint ───────────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    # Rate limit check
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    allowed, limit_msg = rate_limiter.is_allowed(client_ip)
    if not allowed:
        return jsonify({"reply": limit_msg}), 429

    data = request.get_json()
    question = data.get("message", "").strip()
    history = data.get("history", [])  # [{role: "user"|"bot", content: "..."}]

    if not question:
        return jsonify({"reply": "Please enter a question."}), 400

    try:
        firm_name = index.get("firm_name", "our firm")

        # Step 0: Try answering from mini-context.md first
        quick_answer = try_mini_context(question, mini_context, firm_name, history)
        if quick_answer is not None:
            return jsonify({
                "reply": quick_answer,
                "sources": ["mini-context.md"]
            })

        # Step 1: Pick relevant files
        selected_files = pick_files(question, index)

        # Step 2: Generate answer
        reply = answer_question(question, selected_files, index, history)

        return jsonify({
            "reply": reply,
            "sources": selected_files
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"reply": f"Sorry, something went wrong. Please try again later."}), 500


# ─── Lead API endpoint ───────────────────────────────────────────────────────
@app.route("/api/lead", methods=["POST"])
def capture_lead():
    # Demo version: Just acknowledge the lead without storing it
    return jsonify({"success": True})


if __name__ == "__main__":
    print(f"\n  🚀 Server running at http://localhost:5000")
    print(f"  💬 Chat API available at http://localhost:5000/api/chat")
    print(f"  📥 Lead API available at http://localhost:5000/api/lead\n")
    app.run(debug=True, port=5000)
