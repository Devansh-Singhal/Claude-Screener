"""Maps niftyindices 'Industry' labels to tradable NIFTY sectoral indices.

Unmapped industries return None; the screener falls back to NIFTY 200 and
records a warning. Extend this map as new industries appear in the CSV.
"""

INDUSTRY_TO_INDEX: dict[str, str] = {
    "information technology": "NIFTY IT",
    "financial services": "NIFTY FINANCIAL SERVICES",
    "fast moving consumer goods": "NIFTY FMCG",
    "automobile and auto components": "NIFTY AUTO",
    "healthcare": "NIFTY PHARMA",
    "metals & mining": "NIFTY METAL",
    "oil gas & consumable fuels": "NIFTY OIL & GAS",
    "power": "NIFTY ENERGY",
    "consumer durables": "NIFTY CONSUMER DURABLES",
    "realty": "NIFTY REALTY",
    "media entertainment & publication": "NIFTY MEDIA",
}

def sector_index_for(industry: str) -> str | None:
    return INDUSTRY_TO_INDEX.get(industry.strip().lower())
