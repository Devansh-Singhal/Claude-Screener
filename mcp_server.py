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
    sort_by: str = "rs_vs_nifty",
) -> dict:
    """Screen a Nifty universe and return qualifying stocks as JSON.

    Filters: outperform NIFTY 50, outperform sector index, and SMA-short above
    SMA-long over `lookback_days`. Fundamentals fields are null in v1.
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
        sort_by=sort_by,
    )

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
