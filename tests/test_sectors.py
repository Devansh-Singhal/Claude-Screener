from screener import sectors

def test_known_industries_map_to_index():
    assert sectors.sector_index_for("Information Technology") == "NIFTY IT"
    assert sectors.sector_index_for("Financial Services") == "NIFTY FIN SERVICE"
    assert sectors.sector_index_for("Fast Moving Consumer Goods") == "NIFTY FMCG"

def test_unmapped_industry_returns_none():
    assert sectors.sector_index_for("Telecommunication") is None
    assert sectors.sector_index_for("") is None

def test_map_is_case_insensitive():
    assert sectors.sector_index_for("information technology") == "NIFTY IT"
