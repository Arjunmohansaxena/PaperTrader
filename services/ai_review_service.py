"""AI Portfolio Review service.

Takes the same metrics dict produced by services/portfolio_metrics.py
(get_portfolio_metrics) and asks Google's Gemini API to turn it into a
structured, plain-English review: a summary, risk flags, diversification
notes, strengths, and suggestions.

Design notes (see README for the full write-up):
- No math happens here. All numbers come pre-computed from
  portfolio_metrics.py; the model's job is interpretation, not calculation.
- Output is constrained to a JSON schema via Gemini's `responseSchema`, but
  we still defensively parse the response, because "the model followed the
  schema" and "the API call succeeded" are two different failure modes.
- This is explicitly framed (system instruction) as educational commentary
  for a paper-trading app, not financial advice.
"""

import json
import os

import requests
from dotenv import load_dotenv

from utils.exceptions import AIReviewError

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

REQUEST_TIMEOUT_SECONDS = 30

SYSTEM_INSTRUCTION = """You are a portfolio analysis assistant embedded in PaperTrader, a paper \
(simulated) stock trading app used for practice and education. You are given a snapshot of a \
user's virtual portfolio: holdings, sector allocation, cash position, and recent performance.

Write a clear, plain-English review of the portfolio's construction. Focus on:
- Concentration risk (single stocks or sectors that dominate the portfolio)
- Diversification (or lack of it) across sectors and asset types
- Cash allocation (too much idle cash vs. too little buffer)
- Notable performers, called out factually, not as buy/sell signals

Rules:
- This is virtual money in an educational app. Do not give real financial advice, and do not \
issue direct buy/sell recommendations for specific tickers.
- Do not invent numbers. Only reference figures present in the data you were given.
- Keep language plain; avoid unexplained jargon.
- Respond ONLY with JSON matching the required schema. No markdown, no commentary outside the \
JSON object."""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary": {
            "type": "STRING",
            "description": "2-4 sentence plain-English overview of the portfolio's current shape.",
        },
        "risk_flags": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Specific concentration, sector, or cash-allocation risks. Empty array if none.",
        },
        "diversification_notes": {
            "type": "STRING",
            "description": "1-3 sentences on how diversified the portfolio is across sectors/positions.",
        },
        "strengths": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Things the portfolio is doing well. Empty array if none stand out.",
        },
        "suggestions": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "General portfolio-construction ideas to consider (not specific buy/sell calls).",
        },
    },
    "required": ["summary", "risk_flags", "diversification_notes", "strengths", "suggestions"],
}

REQUIRED_FIELDS = RESPONSE_SCHEMA["required"]


def _format_metrics_for_prompt(metrics: dict) -> str:
    """Turns the portfolio_metrics dict into compact, readable text for the
    prompt. Deliberately not just str(metrics) -- Python dict repr wastes
    tokens and is easy for a model to misparse."""
    lines = []

    lines.append(f"Total portfolio value: ${metrics['portfolio_value']:,.2f}")
    lines.append(f"Cash balance: ${metrics['cash_balance']:,.2f} "
                 f"({metrics['stats']['cash_allocation_pct']:.1f}% of portfolio)")
    lines.append(f"Invested capital: ${metrics['invested_capital']:,.2f}")
    lines.append(f"Unrealized P/L: ${metrics['unrealized_pnl']:,.2f}")
    lines.append(f"Realized P/L: ${metrics['realized_pnl']:,.2f}")
    lines.append(f"Total return since account start: {metrics['total_return_pct']:.2f}%")
    lines.append("")

    if metrics["holdings"]:
        lines.append(f"Holdings ({metrics['stats']['num_holdings']} positions):")
        for h in metrics["holdings"]:
            lines.append(
                f"  - {h['symbol']} ({h['name']}): {h['quantity']} shares, "
                f"value ${h['value']:,.2f}, return {h['return_pct']:.2f}%"
            )
    else:
        lines.append("Holdings: none (fully in cash).")
    lines.append("")

    if metrics["sector_allocation"]:
        lines.append("Sector allocation:")
        for row in metrics["sector_allocation"]:
            lines.append(f"  - {row['sector']}: {row['pct']:.1f}%")
    lines.append("")

    if metrics["stats"].get("largest_position"):
        lp = metrics["stats"]["largest_position"]
        lines.append(f"Largest position: {lp['name']} (${lp['value']:,.2f})")
    if metrics["stats"].get("best_performer"):
        bp = metrics["stats"]["best_performer"]
        lines.append(f"Best performer: {bp['name']} ({bp['return_pct']:+.2f}%)")
    if metrics["stats"].get("worst_performer"):
        wp = metrics["stats"]["worst_performer"]
        lines.append(f"Worst performer: {wp['name']} ({wp['return_pct']:+.2f}%)")

    return "\n".join(lines)


def _extract_json_text(candidate_text: str) -> dict:
    """Defensive parse: strips markdown fences if the model added them
    anyway, then json.loads. Raises AIReviewError with a clear message on
    failure rather than letting a stray ValueError bubble up."""
    text = candidate_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIReviewError(f"Model response was not valid JSON: {exc}") from exc

    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        raise AIReviewError(f"Model response missing required field(s): {', '.join(missing)}")

    return data


def generate_portfolio_review(metrics: dict) -> dict:
    """Calls Gemini with the portfolio metrics and returns a dict matching
    RESPONSE_SCHEMA's shape. Raises AIReviewError on any failure (missing
    key, network error, bad response) so the route can turn it into a
    friendly message instead of a 500."""
    if not GEMINI_API_KEY:
        raise AIReviewError("GEMINI_API_KEY is not set; cannot generate an AI review.")

    if metrics is None or (not metrics.get("holdings") and metrics.get("cash_balance", 0) <= 0):
        raise AIReviewError("Not enough portfolio data to generate a review yet.")

    prompt_body = _format_metrics_for_prompt(metrics)

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"role": "user", "parts": [{"text": prompt_body}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
            "temperature": 0.4,
        },
    }

    try:
        response = requests.post(
            GEMINI_URL,
            headers={
                "x-goog-api-key": GEMINI_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise AIReviewError(f"Could not reach Gemini API: {exc}") from exc

    try:
        candidates = data["candidates"]
        parts = candidates[0]["content"]["parts"]
        candidate_text = "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError) as exc:
        raise AIReviewError(f"Unexpected Gemini response shape: {exc}") from exc

    if not candidate_text.strip():
        raise AIReviewError("Gemini returned an empty response.")

    return _extract_json_text(candidate_text)