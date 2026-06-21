import json
import time
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config

IST = timezone(timedelta(hours=5, minutes=30))

class KiteAuthError(Exception):
    pass

def today_trading_date() -> str:
    """Kite tokens expire ~6 AM IST. Before 6 AM, 'today' is still yesterday."""
    now = datetime.now(IST)
    if now.hour < 6:
        now = now - timedelta(days=1)
    return now.strftime("%Y-%m-%d")

def load_token(path: Path) -> dict | None:
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text())

class _RateLimiter:
    """Simple blocking limiter: at most `rate` acquisitions per second."""
    def __init__(self, rate: int):
        self._min_interval = 1.0 / rate
        self._lock = threading.Lock()
        self._next = 0.0
    def acquire(self):
        with self._lock:
            now = time.monotonic()
            wait = self._next - now
            if wait > 0:
                time.sleep(wait)
            self._next = max(now, self._next) + self._min_interval

class KiteClient:
    def __init__(self, kite, token_path: Path = config.TOKEN_PATH):
        tok = load_token(token_path)
        if tok is None or tok.get("date") != today_trading_date():
            raise KiteAuthError(
                "Kite token missing or stale. Use the kite_login tool (in Claude) "
                "or run:  .venv/Scripts/python login.py"
            )
        kite.set_access_token(tok["access_token"])
        self._kite = kite
        self._limiter = _RateLimiter(config.KITE_RATE_LIMIT_PER_SEC)

    def _closes_for(self, token: int, days: int) -> list[float]:
        self._limiter.acquire()
        to_date = datetime.now(IST).date()
        from_date = to_date - timedelta(days=days * 2)  # calendar buffer for weekends
        candles = self._kite.historical_data(token, from_date, to_date, "day")
        return [float(c["close"]) for c in candles]

    def _candles_for(self, token: int, days: int) -> list[dict]:
        self._limiter.acquire()
        to_date = datetime.now(IST).date()
        from_date = to_date - timedelta(days=days * 2)  # calendar buffer for weekends
        candles = self._kite.historical_data(token, from_date, to_date, "day")
        return [{"high": float(c["high"]), "low": float(c["low"]),
                 "close": float(c["close"])} for c in candles]

    def _fetch(self, worker, token_by_symbol: dict[str, int], days: int):
        """Run `worker(token, days)` concurrently per symbol; skip failures."""
        out: dict = {}
        warnings: list[str] = []
        with ThreadPoolExecutor(max_workers=config.KITE_RATE_LIMIT_PER_SEC) as ex:
            futures = {
                ex.submit(worker, tok, days): sym
                for sym, tok in token_by_symbol.items()
            }
            for fut in as_completed(futures):
                sym = futures[fut]
                try:
                    out[sym] = fut.result()
                except Exception as e:
                    warnings.append(f"{sym}: historical fetch failed ({e}), skipped")
        return out, warnings

    def fetch_closes(self, token_by_symbol: dict[str, int], days: int):
        """Returns (closes_by_symbol, warnings). Each value is a list of daily
        closes (oldest first). Failed symbols are skipped. Used for indices."""
        return self._fetch(self._closes_for, token_by_symbol, days)

    def fetch_candles(self, token_by_symbol: dict[str, int], days: int):
        """Returns (candles_by_symbol, warnings). Each value is a list of daily
        {high, low, close} dicts (oldest first). Used for stocks (Supertrend/ATR
        need high & low). Failed symbols are skipped."""
        return self._fetch(self._candles_for, token_by_symbol, days)
