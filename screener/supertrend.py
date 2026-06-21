"""Supertrend indicator (faithful port of the common TradingView Pine v4 script).

Inputs match the chart defaults: ATR period 10, multiplier 3.0, source = hl2,
and Wilder's ATR by default (`wilder=True`, the script's `changeATR=true`); set
`wilder=False` to use a simple moving average of true range instead.

Supertrend is path-dependent: each bar's band depends on the previous bar's
band and trend, so the series must be evaluated oldest-first from the start.
With ~120 daily candles and period 10 the early warmup bars do not affect the
final trend.

Returns a dict for the latest bar:
  trend  : +1 (bullish / up) or -1 (bearish / down)
  signal : "buy" | "sell" | None  (set only when the trend flipped on this bar)
  value  : the Supertrend line value at the latest bar (rounded)
"""


def _true_range(highs, lows, closes) -> list[float]:
    n = len(closes)
    tr = [highs[0] - lows[0]]
    for i in range(1, n):
        prev_close = closes[i - 1]
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - prev_close),
            abs(lows[i] - prev_close),
        ))
    return tr


def _atr(tr: list[float], period: int, wilder: bool) -> list[float | None]:
    """ATR per bar; None for warmup bars before it is defined."""
    n = len(tr)
    atr: list[float | None] = [None] * n
    if wilder:
        atr[period - 1] = sum(tr[:period]) / period          # RMA seed = SMA
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    else:
        for i in range(period - 1, n):
            atr[i] = sum(tr[i - period + 1:i + 1]) / period
    return atr


def supertrend(highs, lows, closes, period: int = 10,
               multiplier: float = 3.0, wilder: bool = True) -> dict:
    n = len(closes)
    if n < period + 2:
        raise ValueError(f"need >= {period + 2} candles, got {n}")

    tr = _true_range(highs, lows, closes)
    atr = _atr(tr, period, wilder)

    start = period - 1                       # first bar with a defined ATR
    up_final = [0.0] * n
    dn_final = [0.0] * n
    trend = [1] * n

    for i in range(start, n):
        src = (highs[i] + lows[i]) / 2.0
        up_basic = src - multiplier * atr[i]
        dn_basic = src + multiplier * atr[i]
        if i == start:
            up_final[i] = up_basic
            dn_final[i] = dn_basic
            trend[i] = 1
            continue
        up_final[i] = (max(up_basic, up_final[i - 1])
                       if closes[i - 1] > up_final[i - 1] else up_basic)
        dn_final[i] = (min(dn_basic, dn_final[i - 1])
                       if closes[i - 1] < dn_final[i - 1] else dn_basic)
        prev = trend[i - 1]
        if prev == -1 and closes[i] > dn_final[i - 1]:
            trend[i] = 1
        elif prev == 1 and closes[i] < up_final[i - 1]:
            trend[i] = -1
        else:
            trend[i] = prev

    last, prev = trend[-1], trend[-2]
    signal = None
    if last == 1 and prev == -1:
        signal = "buy"
    elif last == -1 and prev == 1:
        signal = "sell"
    line = up_final[-1] if last == 1 else dn_final[-1]
    return {"trend": last, "signal": signal, "value": round(line, 2)}
