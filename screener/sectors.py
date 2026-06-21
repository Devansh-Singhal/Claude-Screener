"""Maps niftyindices 'Industry' labels to tradable NIFTY sectoral indices.

Index names are the exact tradingsymbols Kite returns in its NSE instrument
dump (Kite truncates them, e.g. 'NIFTY FIN SERVICE', 'NIFTY OIL AND GAS').
Unmapped industries return None; the screener falls back to the benchmark and
records a warning. Extend this map as new industries appear in the CSV.
"""

INDUSTRY_TO_INDEX: dict[str, str] = {
    "information technology": "NIFTY IT",
    "financial services": "NIFTY FIN SERVICE",
    "fast moving consumer goods": "NIFTY FMCG",
    "automobile and auto components": "NIFTY AUTO",
    "healthcare": "NIFTY HEALTHCARE",
    "metals & mining": "NIFTY METAL",
    "oil gas & consumable fuels": "NIFTY OIL AND GAS",
    "power": "NIFTY ENERGY",
    "consumer durables": "NIFTY CONSR DURBL",
    "realty": "NIFTY REALTY",
    "media entertainment & publication": "NIFTY MEDIA",
    "services": "NIFTY SERV SECTOR",
    "chemicals": "NIFTY CHEMICALS",
}

def sector_index_for(industry: str) -> str | None:
    return INDUSTRY_TO_INDEX.get(industry.strip().lower())
