import pytest
from screener import indicators

def test_sma_is_mean_of_last_period():
    assert indicators.sma([1, 2, 3, 4, 5], 3) == 4.0  # mean(3,4,5)

def test_sma_full_series():
    assert indicators.sma([10, 20, 30], 3) == 20.0

def test_sma_insufficient_data_raises():
    with pytest.raises(ValueError):
        indicators.sma([1, 2], 3)

def test_pct_return_one_day():
    assert indicators.pct_return([100, 110], 1) == pytest.approx(10.0)

def test_pct_return_seven_days():
    closes = [100, 1, 1, 1, 1, 1, 1, 107]  # need days+1 points
    assert indicators.pct_return(closes, 7) == pytest.approx(7.0)

def test_pct_return_insufficient_data_raises():
    with pytest.raises(ValueError):
        indicators.pct_return([100], 7)

def test_relative_strength_is_difference():
    assert indicators.relative_strength(10.0, 4.0) == pytest.approx(6.0)
