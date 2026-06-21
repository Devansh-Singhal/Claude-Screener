# mcp_server.py
"""MCP server exposing a single tool, scan_market, for Claude Desktop."""
from mcp.server.fastmcp import FastMCP

from screener.screen import scan_market as _scan

mcp = FastMCP("screener")

@mcp.tool()
def scan_market(
    universe: str = "nifty200",
    benchmark: str = "NIFTY 50",
    lookback_days: int = 7,
    sma_short: int = 20,
    sma_long: int = 50,
    require_outperform_benchmark: bool = True,
    require_outperform_sector: bool = True,
    require_sma_bullish: bool = True,
    require_supertrend_bullish: bool = False,
    supertrend_period: int = 10,
    supertrend_multiplier: float = 3.0,
    max_pct_below_52w_high: float | None = None,
    sort_by: str = "rs_vs_nifty",
) -> dict:
    """Screen a Nifty universe and return qualifying stocks as JSON.

    Filters: outperform NIFTY 50, outperform sector index, SMA-short above
    SMA-long over `lookback_days`, and (opt-in) require_supertrend_bullish to
    keep only stocks currently in a Supertrend uptrend. Every result also reports
    `supertrend` (+1 up / -1 down), `supertrend_signal` ("buy"/"sell"/null on a
    fresh flip), and `supertrend_value`. Each result also reports `high_52w`,
    `low_52w`, and `pct_from_52w_high` (negative = below the high); set
    max_pct_below_52w_high to keep only stocks within N%% of their 52-week high.
    Fundamentals fields are null in v1.
    """
    return _scan(
        universe=universe,
        benchmark=benchmark,
        lookback_days=lookback_days,
        sma_short=sma_short,
        sma_long=sma_long,
        require_outperform_benchmark=require_outperform_benchmark,
        require_outperform_sector=require_outperform_sector,
        require_sma_bullish=require_sma_bullish,
        require_supertrend_bullish=require_supertrend_bullish,
        supertrend_period=supertrend_period,
        supertrend_multiplier=supertrend_multiplier,
        max_pct_below_52w_high=max_pct_below_52w_high,
        sort_by=sort_by,
    )

@mcp.tool()
def export_watchlist(symbols: list[str], exchange: str = "NSE",
                     section: str | None = None) -> dict:
    """Write the given symbols to a TradingView-importable .txt file (exchange-
    prefixed, comma-separated) in the output folder. Use after a scan to turn
    results into a watchlist: in TradingView, Watchlist menu -> Import, pick the
    returned file. Returns its path, the file content, and the symbol count."""
    from screener import config
    from screener.watchlist import save_watchlist
    path = save_watchlist(symbols, config.OUTPUT_DIR, exchange=exchange, section=section)
    content = path.read_text()
    count = content.replace("###" + (section or ""), "").count(":") if content else 0
    return {"path": str(path), "content": content, "count": count}


@mcp.tool()
def kite_login() -> dict:
    """Start Kite login. Returns a login_url to open in your browser; after you
    log in, the access token is captured and saved automatically (valid until
    ~6 AM IST next day). Call this once per trading day before screening."""
    from screener.auth import start_login_capture
    url = start_login_capture()
    return {
        "login_url": url,
        "instructions": "Open login_url and log in to Zerodha. After the redirect "
                        "completes, the token is saved automatically — then ask me "
                        "to screen. Check kite_login_status to confirm.",
    }


@mcp.tool()
def kite_login_status() -> dict:
    """Report whether a fresh Kite access token is available for today."""
    from screener import config
    from screener.kite_client import load_token, today_trading_date
    tok = load_token(config.TOKEN_PATH)
    logged_in = bool(tok and tok.get("date") == today_trading_date())
    return {"logged_in": logged_in, "token_date": tok.get("date") if tok else None}


if __name__ == "__main__":
    mcp.run()
