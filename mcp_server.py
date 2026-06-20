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

if __name__ == "__main__":
    mcp.run()
