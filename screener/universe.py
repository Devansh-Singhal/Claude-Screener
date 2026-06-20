import csv
import io
from dataclasses import dataclass
import requests

UNIVERSE_URLS = {
    "nifty50": "https://niftyindices.com/IndexConstituent/ind_nifty50list.csv",
    "nifty200": "https://niftyindices.com/IndexConstituent/ind_nifty200list.csv",
    "nifty500": "https://niftyindices.com/IndexConstituent/ind_nifty500list.csv",
}

# niftyindices blocks requests without a browser-like UA.
_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "text/csv,*/*"}

@dataclass(frozen=True)
class Constituent:
    symbol: str
    company: str
    industry: str

def parse_constituents(csv_text: str) -> list[Constituent]:
    reader = csv.DictReader(io.StringIO(csv_text))
    out: list[Constituent] = []
    for row in reader:
        symbol = (row.get("Symbol") or "").strip()
        if not symbol:
            continue
        out.append(Constituent(
            symbol=symbol,
            company=(row.get("Company Name") or "").strip(),
            industry=(row.get("Industry") or "").strip(),
        ))
    return out

def fetch_universe(name: str) -> list[Constituent]:
    if name not in UNIVERSE_URLS:
        raise ValueError(f"unknown universe '{name}'; choose from {list(UNIVERSE_URLS)}")
    resp = requests.get(UNIVERSE_URLS[name], headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    return parse_constituents(resp.text)
