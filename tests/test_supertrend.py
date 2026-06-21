import pytest
from screener import supertrend as st


def _bars(closes, spread=0.5):
    """Build (highs, lows, closes) with a tight symmetric high/low band."""
    highs = [c + spread for c in closes]
    lows = [c - spread for c in closes]
    return highs, lows, closes


def test_sustained_uptrend_is_bullish():
    closes = [100 + i for i in range(40)]      # steadily rising
    highs, lows, closes = _bars(closes)
    out = st.supertrend(highs, lows, closes, period=10, multiplier=3.0)
    assert out["trend"] == 1
    assert out["signal"] is None               # no fresh flip on the last bar


def test_sustained_downtrend_is_bearish():
    closes = [140 - i for i in range(40)]      # steadily falling
    highs, lows, closes = _bars(closes)
    out = st.supertrend(highs, lows, closes, period=10, multiplier=3.0)
    assert out["trend"] == -1


def test_sharp_drop_on_last_bar_emits_sell():
    closes = [100 + i for i in range(40)] + [120]  # long up, then a final plunge
    highs, lows, closes = _bars(closes)
    out = st.supertrend(highs, lows, closes, period=10, multiplier=3.0)
    assert out["trend"] == -1
    assert out["signal"] == "sell"


def test_sharp_rise_on_last_bar_emits_buy():
    closes = [140 - i for i in range(40)] + [125]  # long down, then a final spike
    highs, lows, closes = _bars(closes)
    out = st.supertrend(highs, lows, closes, period=10, multiplier=3.0)
    assert out["trend"] == 1
    assert out["signal"] == "buy"


def test_sma_method_runs_and_returns_trend():
    closes = [100 + i for i in range(40)]
    highs, lows, closes = _bars(closes)
    out = st.supertrend(highs, lows, closes, period=10, multiplier=3.0, wilder=False)
    assert out["trend"] in (1, -1)
    assert "value" in out


def test_insufficient_history_raises():
    closes = [100, 101, 102]
    highs, lows, closes = _bars(closes)
    with pytest.raises(ValueError):
        st.supertrend(highs, lows, closes, period=10, multiplier=3.0)
