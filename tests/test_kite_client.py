import json
import pytest
from screener import kite_client

class FakeKite:
    def __init__(self):
        self.token_set = None
        self.calls = []
    def set_access_token(self, t):
        self.token_set = t
    def historical_data(self, instrument_token, from_date, to_date, interval):
        self.calls.append(instrument_token)
        if instrument_token == 999:  # simulate a bad symbol
            raise RuntimeError("no data")
        c = float(instrument_token)
        return [{"date": "2026-06-20", "high": c + 1, "low": c - 1, "close": c}]

def test_load_token_missing_returns_none(tmp_path):
    assert kite_client.load_token(tmp_path / "nope.json") is None

def test_load_token_reads_valid(tmp_path):
    p = tmp_path / "token.json"
    p.write_text(json.dumps({"access_token": "AAA", "date": "2026-06-21"}))
    assert kite_client.load_token(p) == {"access_token": "AAA", "date": "2026-06-21"}

def test_client_raises_on_stale_token(tmp_path):
    p = tmp_path / "token.json"
    p.write_text(json.dumps({"access_token": "AAA", "date": "1999-01-01"}))
    with pytest.raises(kite_client.KiteAuthError):
        kite_client.KiteClient(FakeKite(), token_path=p)

def test_fetch_many_returns_closes_and_records_failures(tmp_path):
    p = tmp_path / "token.json"
    today = kite_client.today_trading_date()
    p.write_text(json.dumps({"access_token": "AAA", "date": today}))
    fake = FakeKite()
    client = kite_client.KiteClient(fake, token_path=p)
    closes, warnings = client.fetch_closes({"GOOD": 5, "BAD": 999}, days=120)
    assert closes == {"GOOD": [5.0]}
    assert any("BAD" in w for w in warnings)
    assert fake.token_set == "AAA"

def test_fetch_candles_returns_ohlc_and_records_failures(tmp_path):
    p = tmp_path / "token.json"
    p.write_text(json.dumps({"access_token": "AAA",
                             "date": kite_client.today_trading_date()}))
    client = kite_client.KiteClient(FakeKite(), token_path=p)
    candles, warnings = client.fetch_candles({"GOOD": 5, "BAD": 999}, days=120)
    assert candles == {"GOOD": [{"high": 6.0, "low": 4.0, "close": 5.0}]}
    assert any("BAD" in w for w in warnings)
