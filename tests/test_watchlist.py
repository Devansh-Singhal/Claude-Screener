from screener import watchlist as wl


def test_formats_exchange_prefixed_csv():
    assert wl.to_tradingview(["TCS", "INFY"]) == "NSE:TCS,NSE:INFY"

def test_uppercases_and_trims():
    assert wl.to_tradingview([" tcs ", "infy"]) == "NSE:TCS,NSE:INFY"

def test_dedupes_preserving_order():
    assert wl.to_tradingview(["TCS", "INFY", "TCS"]) == "NSE:TCS,NSE:INFY"

def test_custom_exchange():
    assert wl.to_tradingview(["RELIANCE"], exchange="BSE") == "BSE:RELIANCE"

def test_section_header():
    assert wl.to_tradingview(["TCS"], section="Momentum") == "###Momentum,NSE:TCS"

def test_empty_input():
    assert wl.to_tradingview([]) == ""
    assert wl.to_tradingview(["", "  "]) == ""

def test_save_writes_txt(tmp_path):
    path = wl.save_watchlist(["TCS", "INFY"], tmp_path)
    assert path.exists()
    assert path.name.startswith("watchlist_") and path.suffix == ".txt"
    assert path.read_text() == "NSE:TCS,NSE:INFY"
