from dataclasses import dataclass
from datetime import date

from . import indicators
from .sectors import sector_index_for
from .universe import Constituent, fetch_universe

@dataclass
class ScreenParams:
    universe: str = "nifty200"
    benchmark: str = "NIFTY 50"
    lookback_days: int = 7
    sma_short: int = 20
    sma_long: int = 50
    require_outperform_benchmark: bool = True
    require_outperform_sector: bool = True
    require_sma_bullish: bool = True
    min_roe: float | None = None      # accepted, no-op in v1
    max_pe: float | None = None       # accepted, no-op in v1
    min_market_cap: float | None = None  # accepted, no-op in v1
    sort_by: str = "rs_vs_nifty"      # rs_vs_nifty | rs_vs_sector | return7

FALLBACK_SECTOR = "the benchmark"

def run_screen(constituents, closes, nifty_closes, sector_closes,
               fundamentals, params: ScreenParams) -> dict:
    warnings: list[str] = []
    nifty_ret = indicators.pct_return(nifty_closes, params.lookback_days)
    results = []

    for c in constituents:
        series = closes.get(c.symbol)
        if series is None:
            continue  # fetch failure already warned upstream
        try:
            ret = indicators.pct_return(series, params.lookback_days)
            sma_s = indicators.sma(series, params.sma_short)
            sma_l = indicators.sma(series, params.sma_long)
        except ValueError as e:
            warnings.append(f"{c.symbol}: insufficient history ({e}), skipped")
            continue

        index_name = sector_index_for(c.industry)
        sector_series = sector_closes.get(index_name) if index_name else None
        if sector_series is None:
            warnings.append(
                f"{c.symbol}: no sectoral index for Industry '{c.industry}' "
                f"-> fell back to {FALLBACK_SECTOR}"
            )
            sector_ret = nifty_ret  # no sector index -> use benchmark return
        else:
            sector_ret = indicators.pct_return(sector_series, params.lookback_days)

        rs_nifty = indicators.relative_strength(ret, nifty_ret)
        rs_sector = indicators.relative_strength(ret, sector_ret)

        if params.require_outperform_benchmark and rs_nifty <= 0:
            continue
        if params.require_outperform_sector and rs_sector <= 0:
            continue
        if params.require_sma_bullish and not (sma_s > sma_l):
            continue

        f = fundamentals.get(c.symbol, {})
        results.append({
            "symbol": c.symbol,
            "company": c.company,
            "sector": c.industry,
            "pe": f.get("pe"),
            "sector_pe": None,
            "roe": f.get("roe"),
            "roce": f.get("roce"),
            "sma20": round(sma_s, 2),
            "sma50": round(sma_l, 2),
            "return7": round(ret, 2),
            "nifty_return7": round(nifty_ret, 2),
            "sector_return7": round(sector_ret, 2),
            "rs_vs_nifty": round(rs_nifty, 2),
            "rs_vs_sector": round(rs_sector, 2),
        })

    results.sort(key=lambda r: r[params.sort_by], reverse=True)
    return {
        "results": results,
        "warnings": warnings,
        "meta": {
            "universe": params.universe,
            "lookback_days": params.lookback_days,
            "as_of": date.today().isoformat(),
            "count": len(results),
        },
    }


def scan_market(**kwargs) -> dict:
    """Public entrypoint: wires live I/O, then calls run_screen.

    Accepts the same fields as ScreenParams as keyword args.
    """
    from kiteconnect import KiteConnect
    from . import config
    from .kite_client import KiteClient
    from .fundamentals import NullProvider

    params = ScreenParams(**kwargs)
    constituents = fetch_universe(params.universe)

    kite = KiteConnect(api_key=config.api_key())
    client = KiteClient(kite)

    # Resolve NSE equity tokens + index tokens from the instrument dump.
    nse = kite.instruments("NSE")
    eq_token = {i["tradingsymbol"]: i["instrument_token"]
                for i in nse if i.get("instrument_type") == "EQ"}
    idx_token = {i["tradingsymbol"]: i["instrument_token"]
                 for i in nse if i.get("segment") == "INDICES"}

    sym_token = {c.symbol: eq_token[c.symbol]
                 for c in constituents if c.symbol in eq_token}

    needed_indices = {params.benchmark}
    for c in constituents:
        idx = sector_index_for(c.industry)
        if idx:
            needed_indices.add(idx)

    # The benchmark must resolve, or relative strength is undefined and the scan
    # would crash later on an empty series. Fail early with an actionable message.
    if params.benchmark not in idx_token:
        raise ValueError(
            f"Benchmark index '{params.benchmark}' not found in Kite's NSE "
            f"instrument dump. Check the exact tradingsymbol Kite uses."
        )

    # A needed sector index that Kite names differently is dropped silently below;
    # surface it as a warning so the user knows those stocks used the fallback.
    missing_index_warnings = [
        f"sector index '{name}' not found in Kite instrument dump "
        f"-> stocks in it fall back to the benchmark"
        for name in sorted(needed_indices)
        if name not in idx_token
    ]
    index_token = {name: idx_token[name] for name in needed_indices
                   if name in idx_token}

    closes, warnings = client.fetch_closes(sym_token, config.HISTORY_DAYS)
    index_closes, idx_warnings = client.fetch_closes(index_token, config.HISTORY_DAYS)

    nifty_closes = index_closes.get(params.benchmark, [])
    sector_closes = {k: v for k, v in index_closes.items() if k != params.benchmark}

    fundamentals = NullProvider()
    fund_data = fundamentals.get([c.symbol for c in constituents])

    class _DictFund:
        def get(self, sym, default=None):
            return fund_data.get(sym, {})

    out = run_screen(constituents, closes, nifty_closes, sector_closes,
                     _DictFund(), params)
    out["warnings"] = (warnings + idx_warnings + missing_index_warnings
                       + out["warnings"])
    return out
