"""Export symbols as a TradingView-importable watchlist file.

TradingView's "Import watchlist" accepts a plain .txt of exchange-prefixed,
comma-separated symbols (e.g. NSE:TCS,NSE:INFY), with optional ###Section
headers. NSE is the default exchange for Indian equities.
"""
from datetime import datetime
from pathlib import Path


def _items(symbols, exchange: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in symbols:
        if not s or not s.strip():
            continue
        sym = f"{exchange}:{s.strip().upper()}"
        if sym not in seen:
            seen.add(sym)
            out.append(sym)
    return out


def to_tradingview(symbols, exchange: str = "NSE", section: str | None = None) -> str:
    body = ",".join(_items(symbols, exchange))
    if section:
        return f"###{section}," + body if body else f"###{section}"
    return body


def save_watchlist(symbols, out_dir, exchange: str = "NSE",
                   section: str | None = None) -> Path:
    """Write the TradingView watchlist text to out_dir/watchlist_<ts>.txt and
    return its path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"watchlist_{ts}.txt"
    path.write_text(to_tradingview(symbols, exchange, section))
    return path
