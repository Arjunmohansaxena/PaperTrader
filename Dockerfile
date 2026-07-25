FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Flask-SocketIO runs on 5000 by default (see socketio.run(app, ...) in app.py)
EXPOSE 5000

# Secrets are NOT baked in — pass them at `docker run` time instead
ENV PAPERTRADER_SECRET_KEY="" \
    FINNHUB_API_KEY="" \
    GEMINI_API_KEY="" \
    GEMINI_MODEL="gemini-flash-latest"

CMD ["python", "app.py"]
