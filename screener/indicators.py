"""Pure indicator math. No I/O. Closes are oldest-first lists of floats."""

def sma(closes: list[float], period: int) -> float:
    if len(closes) < period:
        raise ValueError(f"need >= {period} closes, got {len(closes)}")
    window = closes[-period:]
    return sum(window) / period

def pct_return(closes: list[float], days: int) -> float:
    if len(closes) < days + 1:
        raise ValueError(f"need >= {days + 1} closes, got {len(closes)}")
    start = closes[-1 - days]
    end = closes[-1]
    return (end / start - 1.0) * 100.0

def relative_strength(asset_return: float, benchmark_return: float) -> float:
    return asset_return - benchmark_return
