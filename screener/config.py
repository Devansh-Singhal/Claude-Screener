import os
from pathlib import Path

TOKEN_PATH = Path.home() / ".screener" / "token.json"
REDIRECT_PORT = 5000

# Scan results are written here (kept, never auto-deleted). Gitignored.
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# Kite historical-data API limit (requests per second).
KITE_RATE_LIMIT_PER_SEC = 3
# Trading-day candles to fetch: lookback + longest SMA + buffer.
HISTORY_DAYS = 120

class ConfigError(Exception):
    pass

def api_key() -> str:
    return _require("KITE_API_KEY")

def api_secret() -> str:
    return _require("KITE_API_SECRET")

def _require(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise ConfigError(f"Environment variable {name} is not set.")
    return val
