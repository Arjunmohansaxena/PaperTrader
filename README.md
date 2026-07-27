# PaperTrader

PaperTrader is a full-stack paper trading platform built with **Python**, **Flask**, and **PostgreSQL** that enables users to simulate stock trading using live market data in a risk-free environment.

The application provides portfolio management, real-time market updates, historical price visualization, watchlists, transaction tracking, and AI-powered portfolio analysis through a clean and responsive web interface.

---

# Live Application

**Application:** https://papertrader-8ma5.onrender.com

---

# Features

## Authentication

* Secure user registration and login
* Password hashing and session management
* Protected application routes

## Paper Trading

* Buy and sell stocks with virtual capital
* Automatic portfolio updates
* Cash balance management
* Complete transaction history

## Portfolio Management

* Real-time portfolio valuation
* Unrealized and realized profit/loss tracking
* Holdings overview
* Portfolio performance metrics

## Market Data

* Live stock prices
* Historical price charts
* Company profiles
* Market news
* Stock search with autocomplete

## Watchlists

* Create and manage personalized watchlists
* Monitor selected stocks in real time

## AI Portfolio Analysis

* Portfolio evaluation using Google Gemini
* Investment observations
* Risk assessment
* Portfolio summaries

## Real-Time Updates

* WebSocket-based portfolio updates
* Live market price synchronization

---

# Technology Stack

| Category                | Technology            |
| ----------------------- | --------------------- |
| Language                | Python                |
| Backend                 | Flask                 |
| Frontend                | HTML, CSS, JavaScript |
| Database                | PostgreSQL (Neon)     |
| Database Driver         | psycopg               |
| Authentication          | Flask Sessions        |
| Real-Time Communication | Flask-SocketIO        |
| Market Data             | Finnhub API           |
| Historical Data         | yfinance              |
| AI Integration          | Google Gemini         |
| Deployment              | Render                |

---

# Architecture

The application follows a layered architecture to separate presentation, business logic, and data access.

```
Client
   │
   ▼
Flask Routes
   │
   ▼
Service Layer
   │
   ▼
Repository Layer
   │
   ▼
Neon PostgreSQL
```

---

# Project Structure

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

# Installation

## Clone the repository

```bash
git clone https://github.com/Arjunmohansaxena/PaperTrader.git

cd PaperTrader
```

## Create a virtual environment

```bash
python -m venv .venv
```

### Linux/macOS

```bash
source .venv/bin/activate
```

### Windows

```bash
.venv\Scripts\activate
```

## Install dependencies

```bash
pip install -r requirements.txt
```

## Configure Environment Variables

Create a `.env` file in the project root.

```env
DATABASE_URL=your_neon_database_url
FINNHUB_API_KEY=your_finnhub_api_key
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=your_secret_key
```

## Start the application

```bash
python app.py
```

The application will be available at:

```
http://localhost:5000
```

---

# Database

The application uses **Neon PostgreSQL** as its primary database.

The database stores:

* User accounts
* Portfolio holdings
* Transactions
* Watchlists
* Portfolio reviews

---

# External Services

### Finnhub

* Live stock prices
* Company information
* Market news
* Real-time market data

### Yahoo Finance (yfinance)

* Historical price data
* Chart generation

### Google Gemini

* AI-powered portfolio analysis
* Portfolio recommendations
* Risk evaluation

---

# Deployment

The application is deployed on **Render** with **Neon PostgreSQL** as the managed cloud database.

Production URL:

https://papertrader-8ma5.onrender.com

---

# Testing

Execute the test suite using:

```bash
pytest
```

---

# Roadmap

Future enhancements include:

* Email verification
* Password reset
* Price alerts and notifications
* Portfolio analytics dashboard
* REST API
* Multi-factor authentication
* Improved mobile responsiveness
* Export portfolio reports
* AI analysis history

---

# License

This project is licensed under the MIT License.

---

# Author

**Arjun Mohan Saxena**

GitHub: https://github.com/Arjunmohansaxena
