# PaperTrader

A full-stack paper trading platform built with **Python**, **Flask**, and **SQLite** that enables users to simulate stock trading using live market data without risking real capital.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-black)
![SQLite](https://img.shields.io/badge/SQLite-Database-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Overview

PaperTrader is a virtual stock trading application designed to replicate the workflow of a real brokerage platform. Users can register, manage a virtual portfolio, execute simulated trades using live market prices, maintain watchlists, review their transaction history, and generate an AI-powered review of their portfolio.

---

## Features

- User authentication with secure password hashing
- Paper trading using virtual funds
- Live stock prices via Finnhub API (REST + WebSocket streaming)
- Company symbol lookup using the SEC Company Ticker Database
- Portfolio management and valuation
- Buy and sell stock simulation
- Transaction history
- Custom watchlists
- Autocomplete stock search
- Market and company news
- AI-powered portfolio review (Google Gemini)
- SQLite database persistence

---

## AI Portfolio Review

On the Portfolio page, an on-demand "Generate Review" button sends the same
metrics already computed for the dashboard (`services/portfolio_metrics.py`)
to Google's Gemini API and gets back a structured analysis:

- **Summary** — plain-English overview of the portfolio's current shape
- **Diversification notes** — how spread out the portfolio is across sectors/positions
- **Risk flags** — concentration risk, sector overexposure, cash allocation issues
- **Strengths** — what the portfolio is doing well
- **Suggestions** — general portfolio-construction ideas, not buy/sell calls

**Design decisions:**

- **On-demand, not automatic.** Every review is a real API call with real
  latency. Auto-generating one on every page load would mean paying for and
  waiting on a call most of the time nobody asked for. A button keeps it
  deliberate.
- **Structured JSON output, not free text.** The response is constrained to
  a fixed schema (via Gemini's `responseSchema`) so each section renders as
  its own card instead of a wall of text, and so the app can defensively
  validate the response rather than trusting free-form output.
- **Persisted, not ephemeral.** Reviews are saved to a `portfolio_reviews`
  table, so the latest review survives a page refresh and can be downloaded
  later, not just immediately after generating it.
- **Framed as education, not advice.** The system prompt explicitly scopes
  this to a paper-trading, educational context and avoids specific buy/sell
  recommendations — this is virtual money, and the feature is designed to
  teach portfolio-construction concepts (diversification, concentration,
  cash allocation), not to issue financial advice.
- **Gemini, chosen for its free tier.** Google AI Studio's Gemini API offers
  a genuinely free, no-credit-card tier generous enough for a project like
  this, with solid structured-output support.
- **Rolling model alias, not a pinned version.** The app defaults to
  `gemini-flash-latest` rather than a dated model ID like `gemini-2.5-flash`,
  since Google frequently retires or restricts access to specific dated
  models — the rolling alias avoids the integration breaking every time
  that happens.

---

## System Architecture

PaperTrader follows a layered architecture:

- **Presentation Layer** – Flask routes and Jinja templates
- **Service Layer** – Business logic, derived metrics, and external API calls (market data, AI review)
- **Repository Layer** – Data access, translating between models and SQL
- **Database Layer** – SQLite persistence
- **External Services**
  - Finnhub API for live market prices and news (REST + WebSocket)
  - yfinance for historical price data
  - SEC Company Ticker Database for symbol lookup
  - Google Gemini API for AI portfolio reviews

*(Architecture diagram to be added here.)*

---

## Conceptual Class Diagram

The core domain models and their relationships:

- User
- Portfolio
- Position
- Transaction
- WatchList
- Market Data Provider
- AI Review Service

*(Class diagram to be added here.)*

---

## Database Schema

Tables:

- `users` — accounts and credentials
- `holdings` — current stock positions per user
- `transactions` — immutable log of every executed trade
- `watchlists` / `watchlist_stocks` — user-defined stock lists
- `portfolio_reviews` — AI-generated portfolio reviews

*(Full SQL schema to be added here.)*

---

## Technology Stack

| Category | Technology |
|-----------|------------|
| Programming Language | Python |
| Web Framework | Flask (+ Flask-SocketIO) |
| Database | SQLite |
| Authentication | Salted SHA-256 password hashing (session-based) |
| Market Data | Finnhub API |
| Historical Prices | yfinance |
| Symbol Lookup | SEC Company Ticker Database |
| AI Portfolio Review | Google Gemini API |
| Frontend | HTML, CSS, JavaScript |
| Version Control | Git & GitHub |

---

## Project Structure

```text
PaperTrader/
│
├── app.py
├── requirements.txt
├── README.md
│
├── models/
├── repositories/
├── database/
│   └── schema.sql
├── services/
├── templates/
├── static/
├── tests/
└── docs/
```

---

## Installation

### Clone the repository

```bash
git clone https://github.com/<your-username>/PaperTrader.git
cd PaperTrader
```

### Create a virtual environment

**Windows**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file in the project root:

```env
FINNHUB_API_KEY=YOUR_API_KEY
SEC_CONTACT_EMAIL=your_email@example.com
SECRET_KEY=your_secret_key
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-flash-latest
```

Get a free Gemini API key (no credit card required) at
[aistudio.google.com](https://aistudio.google.com/app/apikey). The AI
Portfolio Review feature degrades gracefully if this key is absent — the
rest of the app works normally, and the review button will just show an
error when clicked.

`GEMINI_MODEL` is optional and defaults to `gemini-flash-latest`, Google's
rolling alias for the current stable Flash model. Pin it to a specific
dated model only if you have a reason to.

### Run the application

The SQLite schema is applied automatically on startup — no separate
initialization step is required.

```bash
python app.py
```

Open the application in your browser:

```
http://127.0.0.1:5000
```

---

## Testing

```bash
python -m unittest discover -s tests -v
```

---

## Future Enhancements

- Email verification
- Password reset
- Stop-loss and limit orders
- REST API
- PostgreSQL support
- Docker deployment
- Cloud deployment (AWS or Azure)
- Downloadable AI review as PDF (currently plain-text export)
- AI review history page (past reviews are stored, but only the latest is surfaced in the UI)

---

## License

This project is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for additional information.

---

## Author

**Arjun Mohan Saxena**

B.Tech, Indian Institute of Technology Mandi