"""
Flask server that wraps bot.py and serves the website + chat API.

Usage:
    pip install flask openai
    python server.py

Then open http://localhost:5000 in your browser.
"""

import os
import json
from flask import Flask, request, jsonify, send_from_directory
from bot import pick_files, answer_question, load_index

# ─── Flask App ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR)

# Load the index once at startup
index = load_index()


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
    data = request.get_json()
    question = data.get("message", "").strip()

    if not question:
        return jsonify({"reply": "Please enter a question."}), 400

    try:
        # Step 1: Pick relevant files
        selected_files = pick_files(question, index)

        # Step 2: Generate answer
        reply = answer_question(question, selected_files, index)

        return jsonify({
            "reply": reply,
            "sources": selected_files
        })
    except Exception as e:
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
