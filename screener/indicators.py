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

def high_low_52w(highs: list[float], lows: list[float], window: int = 252):
    """Return (highest high, lowest low) over the last `window` bars (or all
    bars if fewer). 252 trading days ~= 52 weeks."""
    n = len(highs)
    if n == 0 or len(lows) != n:
        raise ValueError("need non-empty, equal-length highs and lows")
    w = min(window, n)
    return max(highs[-w:]), min(lows[-w:])

def pct_from_high(last_close: float, high: float) -> float:
    """Percent of last close relative to a reference high; negative = below it.
    e.g. close 95 vs high 100 -> -5.0 (5% below the high)."""
    if high == 0:
        raise ValueError("reference high is zero")
    return (last_close / high - 1.0) * 100.0
