"""Authenticated AI Copilot chat endpoint.

Built as a factory (create_ai_blueprint) rather than a module-level
Blueprint so it can be handed the app's *existing* portfolio_repo and
watchlist_repo instances -- same database connection, same repositories
every other route uses, no second data path (see PHASE_1_AI_COPILOT.md
section 4/11's "do not create a second independent integration").
"""

from flask import Blueprint, jsonify, request, session

from ai.service import ask
from utils.auth import login_required
from utils.exceptions import AICopilotError

MAX_MESSAGE_LENGTH = 1000
MAX_HISTORY_TURNS = 20


def create_ai_blueprint(portfolio_repo, watchlist_repo) -> Blueprint:
    ai_bp = Blueprint("ai", __name__)

    @ai_bp.route("/api/ai/chat", methods=["POST"])
    @login_required
    def ai_chat():
        # The backend determines the authenticated user from the existing
        # session -- the request body never supplies (or is trusted for) a
        # user id, and neither is the LLM ever given one to pass to a tool.
        user_id = session.get("user_id")

        data = request.get_json(silent=True) or {}
        message = str(data.get("message", "")).strip()
        history = data.get("history", [])

        if not message:
            return jsonify({"error": "Message cannot be empty."}), 400
        if len(message) > MAX_MESSAGE_LENGTH:
            return jsonify({
                "error": f"Message is too long (max {MAX_MESSAGE_LENGTH} characters)."
            }), 400
        if not isinstance(history, list):
            history = []
        history = history[-MAX_HISTORY_TURNS:]

        try:
            reply = ask(user_id, portfolio_repo, watchlist_repo, message, history)
        except AICopilotError as exc:
            return jsonify({"error": str(exc)}), 502

        return jsonify({"response": reply})

    return ai_bp
