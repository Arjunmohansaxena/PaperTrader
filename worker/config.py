"""Worker configuration, all from environment variables -- nothing here is
hardcoded, and nothing secret is ever committed (see .env.example)."""

import os

from dotenv import load_dotenv

load_dotenv()

# DATABASE_URL is read directly by database.db_manager.DatabaseManager, and
# FINNHUB_API_KEY directly by services.market_data_provider -- both already
# follow this same "environment variable, no hardcoding" convention, so the
# worker just reuses those modules rather than re-reading the same env vars
# a second time.

WORKER_INTERVAL_SECONDS = int(os.getenv("WORKER_INTERVAL", "15"))
