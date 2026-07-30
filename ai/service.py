"""AI Financial Copilot orchestration.

Owns the LLM client, the tool-call loop, and final response generation.
Uses Gemini's REST API directly (same provider/pattern as
services/ai_review_service.py) with function calling enabled via
ai.tools.TOOL_DECLARATIONS.

Flow per PHASE_1_AI_COPILOT.md section 9:
  user message -> LLM -> does it need a tool? -> yes: call tool, feed
  result back to the LLM -> repeat until the LLM answers in plain text.

The LLM never sees a user_id, a database connection, or raw SQL -- see
ai/tools.py for how AITools binds every tool call to the one authenticated
user for this request.
"""

import os
import time

import requests
from dotenv import load_dotenv

from ai.prompts import SYSTEM_PROMPT
from ai.tools import TOOL_DECLARATIONS, AITools
from utils.exceptions import AICopilotError

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

REQUEST_TIMEOUT_SECONDS = 30
MAX_HISTORY_TURNS = 8

# Hard cap on model -> tool -> model round trips for a single user message,
# so a confused model can't loop forever calling tools and never answering.
MAX_TOOL_CALL_ROUNDS = 5


def _build_initial_contents(history: list[dict], message: str) -> list[dict]:
    contents = []
    for turn in (history or [])[-MAX_HISTORY_TURNS:]:
        role = "user" if turn.get("role") == "user" else "model"
        text = str(turn.get("content", "")).strip()
        if text:
            contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": message}]})
    return contents


RETRYABLE_STATUS_CODES = {429, 503}
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2


def _extract_retry_delay_seconds(response) -> float | None:
    """Gemini's 429 responses include a structured RetryInfo.retryDelay
    (e.g. "8s") telling you exactly how long it wants you to wait --
    honoring that is far more accurate than guessing a fixed backoff."""
    if response is None:
        return None
    try:
        details = response.json().get("error", {}).get("details", [])
    except ValueError:
        return None
    for detail in details:
        delay = detail.get("retryDelay")
        if delay and delay.endswith("s"):
            try:
                return float(delay[:-1])
            except ValueError:
                continue
    return None


def _call_gemini(contents: list[dict]) -> dict:
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "tools": TOOL_DECLARATIONS,
        "generationConfig": {"temperature": 0.2},
    }

    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(
                GEMINI_URL,
                headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            last_exc = exc
            status = exc.response.status_code if exc.response is not None else None
            if status in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                # Prefer Gemini's own suggested delay; fall back to a
                # fixed backoff schedule if it isn't present. Cap it so a
                # server-suggested delay can't stall the request forever.
                suggested = _extract_retry_delay_seconds(exc.response)
                delay = suggested if suggested is not None else RETRY_BACKOFF_SECONDS * (attempt + 1)
                time.sleep(min(delay, 15))
                continue
            break
        except requests.RequestException as exc:
            raise AICopilotError(f"Could not reach the AI service: {exc}") from exc

    exc = last_exc
    status = exc.response.status_code if exc.response is not None else None
    detail = ""
    if exc.response is not None:
        try:
            detail = exc.response.json().get("error", {}).get("message", "")
        except ValueError:
            detail = exc.response.text

    if status == 429:
        raise AICopilotError(
            "The AI Copilot has hit its Gemini API rate limit or free-tier quota. "
            "Please wait a bit and try again, or check the project's plan/billing "
            "and quota at https://ai.google.dev/gemini-api/docs/rate-limits."
            + (f" ({detail})" if detail else "")
        ) from exc

    message = f"Could not reach the AI service: {exc}"
    if detail:
        message += f" -- {detail}"
    raise AICopilotError(message) from exc


def _extract_parts(data: dict) -> list[dict]:
    try:
        return data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError) as exc:
        raise AICopilotError(f"Unexpected AI response shape: {exc}") from exc


def ask(user_id: int, portfolio_repo, watchlist_repo, message: str, history: list[dict] | None = None) -> str:
    """Answers one chat message, running the tool-call loop as many times
    as the model needs (capped at MAX_TOOL_CALL_ROUNDS), and returns the
    final natural-language response text.

    Raises AICopilotError on a missing key, empty message, network error,
    an unparseable response, or exceeding the tool-call round cap.
    """
    if not GEMINI_API_KEY:
        raise AICopilotError("GEMINI_API_KEY is not set; the AI Copilot is not configured.")

    message = (message or "").strip()
    if not message:
        raise AICopilotError("Message cannot be empty.")

    tools = AITools(user_id=user_id, portfolio_repo=portfolio_repo, watchlist_repo=watchlist_repo)
    contents = _build_initial_contents(history, message)

    for _ in range(MAX_TOOL_CALL_ROUNDS):
        data = _call_gemini(contents)
        parts = _extract_parts(data)

        function_call_parts = [p for p in parts if "functionCall" in p]
        text_pieces = [p["text"] for p in parts if "text" in p]

        if not function_call_parts:
            reply_text = "".join(text_pieces).strip()
            if not reply_text:
                raise AICopilotError("The AI service returned an empty response.")
            return reply_text

        # Echo the model's own function-call turn back *exactly as received*
        # -- including any thoughtSignature field alongside functionCall.
        # Gemini 3.x models require that signature to be returned verbatim
        # on the next turn (see thought-signatures docs); rebuilding the
        # part from scratch (e.g. {"functionCall": fc}) silently drops it
        # and the next request 400s with "missing a thought_signature".
        contents.append({"role": "model", "parts": function_call_parts})

        function_response_parts = []
        for part in function_call_parts:
            fc = part["functionCall"]
            result = tools.execute(fc.get("name"), fc.get("args") or {})
            function_response_parts.append({
                "functionResponse": {"name": fc.get("name"), "response": result}
            })
        contents.append({"role": "user", "parts": function_response_parts})

    raise AICopilotError("The AI Copilot could not finish answering (too many tool calls in a row).")