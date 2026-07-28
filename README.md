# PaperTrader

> A production-ready paper trading platform built with Flask, PostgreSQL, WebSockets, and Google Gemini, enabling users to simulate stock trading using live market data in a risk-free environment.

[![Python](...)](...)
[![Flask](...)](...)
[![PostgreSQL](...)](...)
[![Docker](...)](...)
[![MIT License](...)](...)

🌐 **Live Demo:** https://papertrader-8ma5.onrender.com

---

## Screenshots

### Dashboard
(images/working/Screenshot from 2026-07-28 20-58-42.png)

### Portfolio
(images/working/Screenshot from 2026-07-28 20-59-09.png)
(images/working/Screenshot from 2026-07-28 00-08-00.png)
(images/working/Screenshot from 2026-07-28 20-59-22.png)

### AI review
(images/working/Screenshot from 2026-07-28 20-59-45.png)

### Transaction 
(images/working/Screenshot from 2026-07-28 20-59-56.png)

### Company Page
(images/working/Screenshot from 2026-07-28 21-00-56.png)

### News
(images/working/Screenshot from 2026-07-28 21-00-11.png)


## Features

### Authentication
- Secure registration and login
- Password hashing
- Session management

### Paper Trading
- Buy and sell stocks
- Holdings management
- Transaction history
- Cash balance tracking

### Portfolio
- Live valuation
- Profit/Loss tracking
- Holdings overview

### Market Data
- Live stock prices
- Historical charts
- Company profiles
- Market news
- Search with autocomplete

### Watchlists
- Multiple watchlists
- Live monitoring

### AI Portfolio Analysis
- Portfolio evaluation
- Risk assessment
- Investment insights

### Real-Time Updates
- WebSocket-based portfolio synchronization

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

(images/Screenshot from 2026-07-28 22-11-42.png)

---

## Database Schema

(images/Screenshot from 2026-07-28 21-52-46.png)

---

## Development Journey

(images/Screenshot from 2026-07-28 22-02-27.png)

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

```bash
git clone https://github.com/Arjunmohansaxena/PaperTrader.git

cd PaperTrader
```

Create a virtual environment

```bash
python -m venv .venv
```

Linux/macOS

```bash
source .venv/bin/activate
```

Windows

```bash
.venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Create a `.env`

```env
DATABASE_URL=
FINNHUB_API_KEY=
GEMINI_API_KEY=
SECRET_KEY=
```

Run

```bash
python app.py
```

---

## Design Decisions

- Layered architecture separates presentation, business logic, and data access.
- Repository pattern isolates database operations.
- WebSockets provide real-time portfolio updates.
- TTL caching minimizes redundant external API calls.
- PostgreSQL provides reliable cloud-hosted persistence.
- Google Gemini generates AI-powered portfolio reviews.

---

## Deployment

- Dockerized application
- Automated deployment to Render
- PostgreSQL hosted on Neon
- Continuous Integration using GitHub Actions

Production

https://papertrader-8ma5.onrender.com

---

## Roadmap

- Email verification
- Password reset
- REST API
- MFA
- Export portfolio reports
- Portfolio analytics dashboard
- AI history
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

GitHub:
https://github.com/Arjunmohansaxena