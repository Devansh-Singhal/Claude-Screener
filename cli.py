# cli.py
"""Command-line adapter. Example:
.venv/Scripts/python cli.py --universe nifty200 --lookback-days 7
"""
import argparse
import json
import sys

from screener.screen import scan_market

def main():
    p = argparse.ArgumentParser(description="Nifty stock screener")
    p.add_argument("--universe", default="nifty200",
                   choices=["nifty50", "nifty200", "nifty500"])
    p.add_argument("--benchmark", default="NIFTY 50")
    p.add_argument("--lookback-days", type=int, default=7)
    p.add_argument("--sma-short", type=int, default=20)
    p.add_argument("--sma-long", type=int, default=50)
    p.add_argument("--no-outperform-benchmark", action="store_true")
    p.add_argument("--no-outperform-sector", action="store_true")
    p.add_argument("--no-sma-bullish", action="store_true")
    p.add_argument("--supertrend-bullish", action="store_true",
                   help="keep only stocks currently in a Supertrend uptrend")
    p.add_argument("--supertrend-period", type=int, default=10)
    p.add_argument("--supertrend-multiplier", type=float, default=3.0)
    p.add_argument("--sort-by", default="rs_vs_nifty",
                   choices=["rs_vs_nifty", "rs_vs_sector", "return7"])
    a = p.parse_args()

    out = scan_market(
        universe=a.universe,
        benchmark=a.benchmark,
        lookback_days=a.lookback_days,
        sma_short=a.sma_short,
        sma_long=a.sma_long,
        require_outperform_benchmark=not a.no_outperform_benchmark,
        require_outperform_sector=not a.no_outperform_sector,
        require_sma_bullish=not a.no_sma_bullish,
        require_supertrend_bullish=a.supertrend_bullish,
        supertrend_period=a.supertrend_period,
        supertrend_multiplier=a.supertrend_multiplier,
        sort_by=a.sort_by,
    )
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    sys.exit(main())
