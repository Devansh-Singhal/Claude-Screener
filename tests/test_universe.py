from pathlib import Path
from screener import universe

FIXTURE = Path(__file__).parent / "fixtures" / "nifty_sample.csv"

def test_parse_constituents_extracts_rows():
    rows = universe.parse_constituents(FIXTURE.read_text())
    assert len(rows) == 3
    tcs = rows[0]
    assert tcs.symbol == "TCS"
    assert tcs.company == "Tata Consultancy Services Ltd."
    assert tcs.industry == "Information Technology"

def test_parse_handles_whitespace_and_blank_lines():
    text = "Company Name,Industry,Symbol,Series,ISIN Code\n"
    text += " Acme Ltd. , Power , ACME ,EQ,INE000A01000\n\n"
    rows = universe.parse_constituents(text)
    assert len(rows) == 1
    assert rows[0].symbol == "ACME"
    assert rows[0].industry == "Power"

def test_universe_url_known_names():
    assert "nifty200" in universe.UNIVERSE_URLS
    assert universe.UNIVERSE_URLS["nifty200"].endswith(".csv")
