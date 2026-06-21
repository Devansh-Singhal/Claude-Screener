from screener import screen
from screener.universe import Constituent

def _ramp(start, step, n):
    return [start + step * i for i in range(n)]

def test_run_screen_filters_and_sorts():
    # 60 points so SMA50 and 7-day return are defined.
    # STRONG rises fast (beats nifty + sector), WEAK is flat.
    strong = _ramp(100, 1.0, 60)   # +0.6/day, strongly up, sma20>sma50
    weak = [100.0] * 60            # flat: no outperformance
    closes = {"STRONG": strong, "WEAK": weak}
    nifty = _ramp(100, 0.1, 60)
    sector_closes = {"NIFTY IT": _ramp(100, 0.2, 60)}
    constituents = [
        Constituent("STRONG", "Strong Co", "Information Technology"),
        Constituent("WEAK", "Weak Co", "Information Technology"),
    ]
    fundamentals = {"STRONG": {}, "WEAK": {}}

    out = screen.run_screen(
        constituents=constituents,
        closes=closes,
        nifty_closes=nifty,
        sector_closes=sector_closes,
        fundamentals=fundamentals,
        params=screen.ScreenParams(),
    )

    syms = [r["symbol"] for r in out["results"]]
    assert syms == ["STRONG"]          # WEAK filtered out
    r = out["results"][0]
    assert r["sector"] == "Information Technology"
    assert r["pe"] is None and r["roe"] is None and r["roce"] is None
    assert r["rs_vs_nifty"] > 0 and r["rs_vs_sector"] > 0
    assert out["meta"]["universe"] == "nifty200"

def test_save_result_writes_timestamped_json(tmp_path):
    import json
    result = {"results": [], "warnings": [], "meta": {"universe": "nifty50"}}
    path = screen.save_result(result, tmp_path)
    assert path.exists()
    assert path.name.startswith("scan_nifty50_") and path.suffix == ".json"
    saved = json.loads(path.read_text())
    assert saved["meta"]["universe"] == "nifty50"
    assert saved["meta"]["saved_to"] == str(path)  # file records its own path


def test_run_screen_warns_on_unmapped_sector():
    closes = {"ACME": _ramp(100, 1.0, 60)}
    nifty = _ramp(100, 0.1, 60)
    constituents = [Constituent("ACME", "Acme", "Telecommunication")]
    out = screen.run_screen(
        constituents=constituents,
        closes=closes,
        nifty_closes=nifty,
        sector_closes={},
        fundamentals={"ACME": {}},
        params=screen.ScreenParams(require_outperform_sector=False),
    )
    assert any("Telecommunication" in w or "ACME" in w for w in out["warnings"])
