# PaperTrader

> A production-ready paper trading platform built with Flask, PostgreSQL, WebSockets, and Google Gemini, enabling users to simulate stock trading using live market data in a risk-free environment.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1-black?logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-green)

🌐 **Live Demo:** https://papertrader-8ma5.onrender.com

---

## Table of Contents

- [Screenshots](#screenshots)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [Development Journey](#development-journey)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Design Decisions](#design-decisions)
- [Deployment](#deployment)
- [Roadmap](#roadmap)
- [Testing](#testing)
- [License](#license)
- [Author](#author)

---

## Screenshots

### Dashboard

![Dashboard](images/working/Screenshot%20from%202026-07-28%2020-58-42.png)

### Portfolio

![Portfolio](images/working/Screenshot%20from%202026-07-28%2020-59-09.png)

![Portfolio Holdings](images/working/Screenshot%20from%202026-07-28%2000-08-00.png)

![Portfolio Summary](images/working/Screenshot%20from%202026-07-28%2020-59-22.png)

### AI Review

![AI Review](images/working/Screenshot%20from%202026-07-28%2020-59-45.png)

### Transactions

![Transactions](images/working/Screenshot%20from%202026-07-28%2020-59-56.png)

### Company Page

![Company Page](images/working/Screenshot%20from%202026-07-28%2021-00-56.png)

### News

![News](images/working/Screenshot%from%2026-07-28%21-00-11.png)

---

## Features

### Authentication

- Secure user registration and login
- Password hashing
- Session management

### Paper Trading

- Buy and sell stocks at live or manually entered prices
- Holdings management
- Transaction history
- Cash balance tracking

### Portfolio

- Live portfolio valuation
- Profit/Loss tracking
- Holdings overview with company-name-first display (see below)

### Market Data

- Live stock prices, backed by a TTL-cached quote layer (see [Design Decisions](#design-decisions))
- Historical charts
- Company profiles
- Market news, filterable by company
- Search with autocomplete (ticker or company name)

### Human-Readable Identity, Everywhere

Tickers are precise but not always meaningful at a glance. Every surface that
references a stock — the dashboard, holdings table, watchlists, transaction
history, company page, and news — resolves and displays the **company name**
first, with the ticker shown as a secondary, muted tag rather than the
primary label. Name resolution is centralized in a single shared helper
(`get_display_name`) so the behavior is consistent across the entire app
instead of being reimplemented per page.

### Watchlists

- Multiple watchlists per user
- Live monitoring of tracked symbols
- **One-click "add to watchlist" from the company page** — a single dropdown
  lists only the watchlists a stock isn't already in, so adding it is a
  one-select-one-click action instead of hunting through a list of buttons.
  Watchlist actions taken from the company page redirect back to that same
  page instead of bouncing the user away, so context is never lost mid-task.

### AI Portfolio Analysis

- Portfolio evaluation
- Risk assessment
- Investment insights powered by Google Gemini

### Real-Time Updates

- WebSocket-based, low-latency price and portfolio synchronization
- A single unified ingestion point (`_emit_price_updates`) handles both the
  live WebSocket feed and a REST fallback loop, so every downstream consumer
  (UI, caching, future order matching) sees one consistent stream regardless
  of where a given price update originated

---

## Technology Stack

| Category | Technology |
|----------|------------|
| Backend | Flask |
| Language | Python |
| Frontend | HTML, CSS, JavaScript |
| Database | PostgreSQL (Neon) |
| ORM / Driver | psycopg |
| Authentication | Flask Sessions |
| Real-Time | Flask-SocketIO |
| Market Data | Finnhub |
| Historical Data | yfinance |
| AI | Google Gemini |
| Deployment | Render |
| Containerization | Docker |

---

## Architecture

![Architecture](images/Screenshot%20from%202026-07-28%2022-11-42.png)

---

## Database Schema

![Database Schema](images/Screenshot%20from%202026-07-28%2021-52-46.png)

---

## Development Journey

![Development Journey](images/Screenshot%20from%202026-07-28%2022-02-27.png)

---

## Project Structure

```text
PaperTrader/
│
├── app.py
├── main.py
├── requirements.txt
├── Dockerfile
├── database/
├── models/
├── repositories/
├── services/
├── static/
├── templates/
├── tests/
└── README.md
```

---

## Installation

Clone the repository.

```bash
git clone https://github.com/Arjunmohansaxena/PaperTrader.git
cd PaperTrader
```

Create a virtual environment.

```bash
python -m venv .venv
```

Activate the environment.

**Linux / macOS**

```bash
source .venv/bin/activate
```

**Windows**

```bash
.venv\Scripts\activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Create a `.env` file.

```env
DATABASE_URL=
FINNHUB_API_KEY=
GEMINI_API_KEY=
SECRET_KEY=
```

Run the application.

```bash
python app.py
```

---

## Design Decisions

- **Layered architecture** separates presentation (routes/templates),
  business logic (services/models), and data access (repositories), so each
  layer can be reasoned about and tested independently.
- **Repository pattern** isolates every SQL statement behind a small,
  purpose-built class per domain object (users, portfolios, watchlists,
  reviews), keeping route handlers free of raw database code.
- **Centralized, cached identity resolution.** Company-name lookups
  (`get_display_name`) are resolved once behind a shared in-process cache
  rather than being fetched or hand-formatted per page — every view that
  needs a human-readable name calls the same function and gets the same
  answer, with no redundant API calls for a name that essentially never
  changes.
- **TTL-based caching for live market data.** Live quote lookups
  (`get_stock_quote`) sit behind a short time-to-live (TTL) cache rather
  than either fetching on every call or caching indefinitely. A stock's
  price changes constantly, but the dashboard, watchlists, and company page
  can each trigger a lookup per holding on every single page load — without
  a cache, a user with 15 holdings could trigger 15 real Finnhub calls per
  refresh. A short TTL (10 seconds) caps that cost while keeping the
  displayed price close enough to real time for a *viewing* use case (trade
  execution still resolves a fresh price at the moment of the trade, not a
  cached one). Failed lookups are deliberately never cached, so a
  temporarily unavailable symbol retries on the very next request instead
  of appearing "stuck" for the rest of the TTL window. The cache itself is a
  thread-safe, in-process structure — the right tool for a single-process
  deployment, with a documented upgrade path to a shared store like Redis
  if the app ever scales to multiple instances behind a load balancer.
- **WebSockets for real-time state**, funneled through one shared
  `_emit_price_updates` entry point regardless of whether a tick originated
  from the live Finnhub stream or the REST fallback loop, so every
  consumer of price data sees a single consistent feed.
- **PostgreSQL** for reliable, cloud-hosted persistence, with explicit
  transaction boundaries used wherever a multi-statement write must
  succeed or fail as a single atomic unit.
- **Google Gemini** generates structured, disclaimer-bound AI portfolio
  reviews — deliberately scoped to education and risk commentary rather
  than explicit buy/sell recommendations.

---

## Deployment

- Dockerized application
- Automated deployment to Render
- PostgreSQL hosted on Neon
- Continuous Integration using GitHub Actions

### Production

https://papertrader-8ma5.onrender.com

---

## Roadmap

- Limit and stop-loss orders, matched against live price ticks
- Email verification
- Password reset
- REST API
- Multi-factor authentication (MFA)
- Export portfolio reports
- Portfolio analytics dashboard (benchmarking, volatility, drawdown)
- AI review history
- Rate limiting on authentication and API routes
- Mobile responsiveness improvements

---

## Testing

```bash
pytest
```

---

## License

MIT License

---

## Author

**Arjun Mohan Saxena**

GitHub: https://github.com/Arjunmohansaxena