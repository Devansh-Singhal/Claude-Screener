from screener.fundamentals import NullProvider, FundamentalsProvider

def test_null_provider_returns_empty_dict_per_symbol():
    p = NullProvider()
    out = p.get(["TCS", "INFY"])
    assert out == {"TCS": {}, "INFY": {}}

def test_null_provider_is_a_provider():
    assert isinstance(NullProvider(), FundamentalsProvider)
