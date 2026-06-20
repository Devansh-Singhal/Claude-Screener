# Stock Screener for Claude — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python stock screener exposing a single `scan_market` operation (as a library, a CLI, and an MCP server) so Claude can screen the Nifty universe in one tool call.

**Architecture:** All logic lives in the `screener/` package; `cli.py` and `mcp_server.py` are thin adapters. Pure computation (indicators, screening orchestration, parsing) is separated from I/O (Kite, niftyindices HTTP) so the core is unit-tested with no network. Price data comes from Kite Connect; universe + sector labels from niftyindices.com CSVs. Fundamentals are a placeholder interface (no-op in v1).

**Tech Stack:** Python 3.12, `kiteconnect`, `pandas`, `requests`, `mcp` (FastMCP), `pytest`.

**Conventions for every task:**
- Run Python via the project venv: `.venv/Scripts/python` (Windows). All commands below assume the repo root as CWD.
- Source of truth for the design: `docs/superpowers/specs/2026-06-21-stock-screener-design.md`.

---

### Task 0: Project scaffold, venv, dependencies, git

**Files:**
- Create: `requirements.txt`, `.gitignore`, `screener/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Initialize git and create the package skeleton**

```bash
cd "C:/Users/ASUS/Desktop/Claude-Screener"
git init
mkdir -p screener tests
touch screener/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `requirements.txt`**

```
kiteconnect>=5.0.0
pandas>=2.2.0
requests>=2.31.0
mcp>=1.2.0
pytest>=8.0.0
```

- [ ] **Step 3: Write `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.env
```

- [ ] **Step 4: Create venv and install dependencies**

Run:
```bash
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/python -m pip install -r requirements.txt
```
Expected: all packages install without error.

- [ ] **Step 5: Verify pytest runs**

Run: `.venv/Scripts/python -m pytest -q`
Expected: "no tests ran" (exit code 5) — confirms pytest is installed.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .gitignore screener/__init__.py tests/__init__.py
git commit -m "chore: scaffold screener package and dependencies"
```

---

### Task 1: `config.py` — paths and credentials

**Files:**
- Create: `screener/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import os
from screener import config

def test_token_path_under_home():
    assert config.TOKEN_PATH.name == "token.json"
    assert config.TOKEN_PATH.parent.name == ".screener"

def test_credentials_read_from_env(monkeypatch):
    monkeypatch.setenv("KITE_API_KEY", "abc")
    monkeypatch.setenv("KITE_API_SECRET", "xyz")
    assert config.api_key() == "abc"
    assert config.api_secret() == "xyz"

def test_missing_credentials_raises(monkeypatch):
    monkeypatch.delenv("KITE_API_KEY", raising=False)
    try:
        config.api_key()
        assert False, "expected error"
    except config.ConfigError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: screener.config`.

- [ ] **Step 3: Write minimal implementation**

```python
# screener/config.py
import os
from pathlib import Path

TOKEN_PATH = Path.home() / ".screener" / "token.json"
REDIRECT_PORT = 5000

# Kite historical-data API limit (requests per second).
KITE_RATE_LIMIT_PER_SEC = 3
# Trading-day candles to fetch: lookback + longest SMA + buffer.
HISTORY_DAYS = 120

class ConfigError(Exception):
    pass

def api_key() -> str:
    return _require("KITE_API_KEY")

def api_secret() -> str:
    return _require("KITE_API_SECRET")

def _require(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise ConfigError(f"Environment variable {name} is not set.")
    return val
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add screener/config.py tests/test_config.py
git commit -m "feat: config with token path and env credentials"
```

---

### Task 2: `indicators.py` — SMA, returns, relative strength (pure math, TDD)

**Files:**
- Create: `screener/indicators.py`
- Test: `tests/test_indicators.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_indicators.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_indicators.py -v`
Expected: FAIL — `ModuleNotFoundError: screener.indicators`.

- [ ] **Step 3: Write minimal implementation**

```python
# screener/indicators.py
"""Pure indicator math. No I/O. Closes are oldest-first lists of floats."""

def sma(closes: list[float], period: int) -> float:
    if len(closes) < period:
        raise ValueError(f"need >= {period} closes, got {len(closes)}")
    window = closes[-period:]
    return sum(window) / period

def pct_return(closes: list[float], days: int) -> float:
    if len(closes) < days + 1:
        raise ValueError(f"need >= {days + 1} closes, got {len(closes)}")
    start = closes[-1 - days]
    end = closes[-1]
    return (end / start - 1.0) * 100.0

def relative_strength(asset_return: float, benchmark_return: float) -> float:
    return asset_return - benchmark_return
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_indicators.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add screener/indicators.py tests/test_indicators.py
git commit -m "feat: SMA, pct_return, relative_strength indicators"
```

---

### Task 3: `universe.py` — parse niftyindices constituents

**Files:**
- Create: `screener/universe.py`
- Test: `tests/test_universe.py`, `tests/fixtures/nifty_sample.csv`

- [ ] **Step 1: Create the fixture CSV**

```
# tests/fixtures/nifty_sample.csv
Company Name,Industry,Symbol,Series,ISIN Code
Tata Consultancy Services Ltd.,Information Technology,TCS,EQ,INE467B01029
HDFC Bank Ltd.,Financial Services,HDFCBANK,EQ,INE040A01034
Sun Pharmaceutical Industries Ltd.,Healthcare,SUNPHARMA,EQ,INE044A01036
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_universe.py
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_universe.py -v`
Expected: FAIL — `ModuleNotFoundError: screener.universe`.

- [ ] **Step 4: Write minimal implementation**

```python
# screener/universe.py
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_universe.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add screener/universe.py tests/test_universe.py tests/fixtures/nifty_sample.csv
git commit -m "feat: niftyindices constituent fetch and parse"
```

---

### Task 4: `sectors.py` — Industry → NIFTY sectoral index map

**Files:**
- Create: `screener/sectors.py`
- Test: `tests/test_sectors.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sectors.py
from screener import sectors

def test_known_industries_map_to_index():
    assert sectors.sector_index_for("Information Technology") == "NIFTY IT"
    assert sectors.sector_index_for("Financial Services") == "NIFTY FINANCIAL SERVICES"
    assert sectors.sector_index_for("Fast Moving Consumer Goods") == "NIFTY FMCG"

def test_unmapped_industry_returns_none():
    assert sectors.sector_index_for("Telecommunication") is None
    assert sectors.sector_index_for("") is None

def test_map_is_case_insensitive():
    assert sectors.sector_index_for("information technology") == "NIFTY IT"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_sectors.py -v`
Expected: FAIL — `ModuleNotFoundError: screener.sectors`.

- [ ] **Step 3: Write minimal implementation**

```python
# screener/sectors.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_sectors.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add screener/sectors.py tests/test_sectors.py
git commit -m "feat: industry to NIFTY sectoral index map"
```

---

### Task 5: `fundamentals.py` — provider interface + NullProvider

**Files:**
- Create: `screener/fundamentals.py`
- Test: `tests/test_fundamentals.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fundamentals.py
from screener.fundamentals import NullProvider, FundamentalsProvider

def test_null_provider_returns_empty_dict_per_symbol():
    p = NullProvider()
    out = p.get(["TCS", "INFY"])
    assert out == {"TCS": {}, "INFY": {}}

def test_null_provider_is_a_provider():
    assert isinstance(NullProvider(), FundamentalsProvider)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_fundamentals.py -v`
Expected: FAIL — `ModuleNotFoundError: screener.fundamentals`.

- [ ] **Step 3: Write minimal implementation**

```python
# screener/fundamentals.py
"""Pluggable fundamentals source. v1 ships NullProvider (no fundamentals).

A future FMP/yfinance provider implements get() returning, per symbol, any of:
pe, roe, roce, market_cap. Missing keys serialize as null downstream.
"""
from abc import ABC, abstractmethod

class FundamentalsProvider(ABC):
    @abstractmethod
    def get(self, symbols: list[str]) -> dict[str, dict]:
        ...

class NullProvider(FundamentalsProvider):
    def get(self, symbols: list[str]) -> dict[str, dict]:
        return {s: {} for s in symbols}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_fundamentals.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add screener/fundamentals.py tests/test_fundamentals.py
git commit -m "feat: fundamentals provider interface and NullProvider"
```

---

### Task 6: `kite_client.py` — token loading + concurrent candle fetch

**Files:**
- Create: `screener/kite_client.py`
- Test: `tests/test_kite_client.py`

The `KiteClient` wraps an injected `kite`-like object (duck-typed: needs
`set_access_token`, `instruments`, `historical_data`) so tests use a fake and
never hit the network.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_kite_client.py
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
        return [{"date": "2026-06-20", "close": float(instrument_token)}]

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_kite_client.py -v`
Expected: FAIL — `ModuleNotFoundError: screener.kite_client`.

- [ ] **Step 3: Write minimal implementation**

```python
# screener/kite_client.py
import json
import time
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config

IST = timezone(timedelta(hours=5, minutes=30))

class KiteAuthError(Exception):
    pass

def today_trading_date() -> str:
    """Kite tokens expire ~6 AM IST. Before 6 AM, 'today' is still yesterday."""
    now = datetime.now(IST)
    if now.hour < 6:
        now = now - timedelta(days=1)
    return now.strftime("%Y-%m-%d")

def load_token(path: Path) -> dict | None:
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text())

class _RateLimiter:
    """Simple blocking limiter: at most `rate` acquisitions per second."""
    def __init__(self, rate: int):
        self._min_interval = 1.0 / rate
        self._lock = threading.Lock()
        self._next = 0.0
    def acquire(self):
        with self._lock:
            now = time.monotonic()
            wait = self._next - now
            if wait > 0:
                time.sleep(wait)
            self._next = max(now, self._next) + self._min_interval

class KiteClient:
    def __init__(self, kite, token_path: Path = config.TOKEN_PATH):
        tok = load_token(token_path)
        if tok is None or tok.get("date") != today_trading_date():
            raise KiteAuthError(
                "Kite token missing or stale. Run:  .venv/Scripts/python login.py"
            )
        kite.set_access_token(tok["access_token"])
        self._kite = kite
        self._limiter = _RateLimiter(config.KITE_RATE_LIMIT_PER_SEC)

    def _closes_for(self, token: int, days: int) -> list[float]:
        self._limiter.acquire()
        to_date = datetime.now(IST).date()
        from_date = to_date - timedelta(days=days * 2)  # calendar buffer for weekends
        candles = self._kite.historical_data(token, from_date, to_date, "day")
        return [float(c["close"]) for c in candles]

    def fetch_closes(self, token_by_symbol: dict[str, int], days: int):
        """Returns (closes_by_symbol, warnings). Failed symbols are skipped."""
        closes: dict[str, list[float]] = {}
        warnings: list[str] = []
        with ThreadPoolExecutor(max_workers=config.KITE_RATE_LIMIT_PER_SEC) as ex:
            futures = {
                ex.submit(self._closes_for, tok, days): sym
                for sym, tok in token_by_symbol.items()
            }
            for fut in as_completed(futures):
                sym = futures[fut]
                try:
                    closes[sym] = fut.result()
                except Exception as e:
                    warnings.append(f"{sym}: historical fetch failed ({e}), skipped")
        return closes, warnings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_kite_client.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add screener/kite_client.py tests/test_kite_client.py
git commit -m "feat: KiteClient with token check, rate limiting, concurrent fetch"
```

---

### Task 7: `screen.py` — pure orchestration (`run_screen`) + public `scan_market`

**Files:**
- Create: `screener/screen.py`
- Test: `tests/test_screen.py`

`run_screen` is pure: it takes already-fetched closes and produces the result
dict. `scan_market` wires real I/O (universe fetch, token resolution, Kite
fetch) then calls `run_screen`. Only `run_screen` is unit-tested.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_screen.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_screen.py -v`
Expected: FAIL — `ModuleNotFoundError: screener.screen`.

- [ ] **Step 3: Write minimal implementation**

```python
# screener/screen.py
from dataclasses import dataclass
from datetime import date

from . import indicators
from .sectors import sector_index_for
from .universe import Constituent, fetch_universe

@dataclass
class ScreenParams:
    universe: str = "nifty200"
    benchmark: str = "NIFTY 50"
    lookback_days: int = 7
    sma_short: int = 20
    sma_long: int = 50
    require_outperform_benchmark: bool = True
    require_outperform_sector: bool = True
    require_sma_bullish: bool = True
    min_roe: float | None = None      # accepted, no-op in v1
    max_pe: float | None = None       # accepted, no-op in v1
    min_market_cap: float | None = None  # accepted, no-op in v1
    sort_by: str = "rs_vs_nifty"      # rs_vs_nifty | rs_vs_sector | return7

FALLBACK_SECTOR = "NIFTY 200"

def run_screen(constituents, closes, nifty_closes, sector_closes,
               fundamentals, params: ScreenParams) -> dict:
    warnings: list[str] = []
    nifty_ret = indicators.pct_return(nifty_closes, params.lookback_days)
    results = []

    for c in constituents:
        series = closes.get(c.symbol)
        if series is None:
            continue  # fetch failure already warned upstream
        try:
            ret = indicators.pct_return(series, params.lookback_days)
            sma_s = indicators.sma(series, params.sma_short)
            sma_l = indicators.sma(series, params.sma_long)
        except ValueError as e:
            warnings.append(f"{c.symbol}: insufficient history ({e}), skipped")
            continue

        index_name = sector_index_for(c.industry)
        sector_series = sector_closes.get(index_name) if index_name else None
        if sector_series is None:
            warnings.append(
                f"{c.symbol}: no sectoral index for Industry '{c.industry}' "
                f"-> fell back to {FALLBACK_SECTOR}"
            )
            sector_ret = nifty_ret  # NIFTY 200 fallback ~ benchmark proxy
        else:
            sector_ret = indicators.pct_return(sector_series, params.lookback_days)

        rs_nifty = indicators.relative_strength(ret, nifty_ret)
        rs_sector = indicators.relative_strength(ret, sector_ret)

        if params.require_outperform_benchmark and rs_nifty <= 0:
            continue
        if params.require_outperform_sector and rs_sector <= 0:
            continue
        if params.require_sma_bullish and not (sma_s > sma_l):
            continue

        f = fundamentals.get(c.symbol, {})
        results.append({
            "symbol": c.symbol,
            "company": c.company,
            "sector": c.industry,
            "pe": f.get("pe"),
            "sector_pe": None,
            "roe": f.get("roe"),
            "roce": f.get("roce"),
            "sma20": round(sma_s, 2),
            "sma50": round(sma_l, 2),
            "return7": round(ret, 2),
            "nifty_return7": round(nifty_ret, 2),
            "sector_return7": round(sector_ret, 2),
            "rs_vs_nifty": round(rs_nifty, 2),
            "rs_vs_sector": round(rs_sector, 2),
        })

    results.sort(key=lambda r: r[params.sort_by], reverse=True)
    return {
        "results": results,
        "warnings": warnings,
        "meta": {
            "universe": params.universe,
            "lookback_days": params.lookback_days,
            "as_of": date.today().isoformat(),
            "count": len(results),
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_screen.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Add the I/O wiring `scan_market` (not unit-tested; validated at smoke test)**

Append to `screener/screen.py`:

```python
def scan_market(**kwargs) -> dict:
    """Public entrypoint: wires live I/O, then calls run_screen.

    Accepts the same fields as ScreenParams as keyword args.
    """
    from kiteconnect import KiteConnect
    from . import config
    from .kite_client import KiteClient
    from .fundamentals import NullProvider

    params = ScreenParams(**kwargs)
    constituents = fetch_universe(params.universe)

    kite = KiteConnect(api_key=config.api_key())
    client = KiteClient(kite)

    # Resolve NSE equity tokens + index tokens from the instrument dump.
    nse = kite.instruments("NSE")
    eq_token = {i["tradingsymbol"]: i["instrument_token"]
                for i in nse if i.get("segment") == "NSE"}
    idx_token = {i["tradingsymbol"]: i["instrument_token"]
                 for i in nse if i.get("segment") == "INDICES"}

    sym_token = {c.symbol: eq_token[c.symbol]
                 for c in constituents if c.symbol in eq_token}

    needed_indices = {params.benchmark}
    for c in constituents:
        idx = sector_index_for(c.industry)
        if idx:
            needed_indices.add(idx)
    index_token = {name: idx_token[name] for name in needed_indices
                   if name in idx_token}

    closes, warnings = client.fetch_closes(sym_token, config.HISTORY_DAYS)
    index_closes, idx_warnings = client.fetch_closes(index_token, config.HISTORY_DAYS)

    nifty_closes = index_closes.get(params.benchmark, [])
    sector_closes = {k: v for k, v in index_closes.items() if k != params.benchmark}

    fundamentals = NullProvider()
    fund_data = fundamentals.get([c.symbol for c in constituents])

    class _DictFund:
        def get(self, sym, default=None):
            return fund_data.get(sym, {})

    out = run_screen(constituents, closes, nifty_closes, sector_closes,
                     _DictFund(), params)
    out["warnings"] = warnings + idx_warnings + out["warnings"]
    return out
```

- [ ] **Step 6: Run the full suite**

Run: `.venv/Scripts/python -m pytest -v`
Expected: PASS (all tests across all files).

- [ ] **Step 7: Commit**

```bash
git add screener/screen.py tests/test_screen.py
git commit -m "feat: run_screen orchestration and scan_market I/O wiring"
```

---

### Task 8: `login.py` — daily Kite token (autograb + paste fallback)

**Files:**
- Create: `login.py`

Not unit-tested (interactive browser flow); validated manually.

- [ ] **Step 1: Write `login.py`**

```python
# login.py
"""Run once each trading morning to mint a Kite access token.

Setup (one time): in developer.kite.trade, set the app Redirect URL to
http://127.0.0.1:5000/  so autograb works. Otherwise the paste fallback runs.
"""
import json
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from kiteconnect import KiteConnect
from screener import config

def _autograb(kite) -> str | None:
    token_holder = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.urlparse(self.path).query
            rt = urllib.parse.parse_qs(q).get("request_token", [None])[0]
            token_holder["request_token"] = rt
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Login OK. You can close this tab.")
        def log_message(self, *a):  # silence server logs
            pass

    try:
        server = HTTPServer(("127.0.0.1", config.REDIRECT_PORT), Handler)
    except OSError:
        return None  # port busy -> fall back to paste
    print(f"Opening browser; listening on http://127.0.0.1:{config.REDIRECT_PORT}/ ...")
    webbrowser.open(kite.login_url())
    threading.Thread(target=server.handle_request).start()
    # Block until the single request is handled.
    while "request_token" not in token_holder:
        pass
    return token_holder["request_token"]

def _paste(kite) -> str:
    print("Open this URL, log in, then copy the request_token from the address bar:")
    print("  ", kite.login_url())
    return input("request_token: ").strip()

def main():
    kite = KiteConnect(api_key=config.api_key())
    request_token = _autograb(kite) or _paste(kite)
    data = kite.generate_session(request_token, api_secret=config.api_secret())
    config.TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    from screener.kite_client import today_trading_date
    config.TOKEN_PATH.write_text(json.dumps({
        "access_token": data["access_token"],
        "date": today_trading_date(),
    }))
    print(f"Saved token to {config.TOKEN_PATH}")

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify it imports without running the flow**

Run: `.venv/Scripts/python -c "import login; print('ok')"`
Expected: prints `ok` (no syntax/import errors).

- [ ] **Step 3: Commit**

```bash
git add login.py
git commit -m "feat: daily Kite login helper with autograb and paste fallback"
```

---

### Task 9: `cli.py` — argparse adapter

**Files:**
- Create: `cli.py`

- [ ] **Step 1: Write `cli.py`**

```python
# cli.py
"""Command-line adapter. Example:
.venv/Scripts/python cli.py --universe nifty200 --lookback-days 7
"""
import argparse
import json
import sys

from screener.screen import scan_market

def main():
    p = argparse.ArgumentParser(description="Nifty stock screener")
    p.add_argument("--universe", default="nifty200",
                   choices=["nifty50", "nifty200", "nifty500"])
    p.add_argument("--benchmark", default="NIFTY 50")
    p.add_argument("--lookback-days", type=int, default=7)
    p.add_argument("--sma-short", type=int, default=20)
    p.add_argument("--sma-long", type=int, default=50)
    p.add_argument("--no-outperform-benchmark", action="store_true")
    p.add_argument("--no-outperform-sector", action="store_true")
    p.add_argument("--no-sma-bullish", action="store_true")
    p.add_argument("--sort-by", default="rs_vs_nifty",
                   choices=["rs_vs_nifty", "rs_vs_sector", "return7"])
    a = p.parse_args()

    out = scan_market(
        universe=a.universe,
        benchmark=a.benchmark,
        lookback_days=a.lookback_days,
        sma_short=a.sma_short,
        sma_long=a.sma_long,
        require_outperform_benchmark=not a.no_outperform_benchmark,
        require_outperform_sector=not a.no_outperform_sector,
        require_sma_bullish=not a.no_sma_bullish,
        sort_by=a.sort_by,
    )
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify argparse help works (no network)**

Run: `.venv/Scripts/python cli.py --help`
Expected: prints usage with all options, exit 0.

- [ ] **Step 3: Commit**

```bash
git add cli.py
git commit -m "feat: CLI adapter for scan_market"
```

---

### Task 10: `mcp_server.py` — MCP adapter exposing one tool

**Files:**
- Create: `mcp_server.py`

- [ ] **Step 1: Write `mcp_server.py`**

```python
# mcp_server.py
"""MCP server exposing a single tool, scan_market, for Claude Desktop."""
from mcp.server.fastmcp import FastMCP

from screener.screen import scan_market as _scan

mcp = FastMCP("screener")

@mcp.tool()
def scan_market(
    universe: str = "nifty200",
    benchmark: str = "NIFTY 50",
    lookback_days: int = 7,
    sma_short: int = 20,
    sma_long: int = 50,
    require_outperform_benchmark: bool = True,
    require_outperform_sector: bool = True,
    require_sma_bullish: bool = True,
    sort_by: str = "rs_vs_nifty",
) -> dict:
    """Screen a Nifty universe and return qualifying stocks as JSON.

    Filters: outperform NIFTY 50, outperform sector index, and SMA-short above
    SMA-long over `lookback_days`. Fundamentals fields are null in v1.
    """
    return _scan(
        universe=universe,
        benchmark=benchmark,
        lookback_days=lookback_days,
        sma_short=sma_short,
        sma_long=sma_long,
        require_outperform_benchmark=require_outperform_benchmark,
        require_outperform_sector=require_outperform_sector,
        require_sma_bullish=require_sma_bullish,
        sort_by=sort_by,
    )

if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 2: Verify it imports**

Run: `.venv/Scripts/python -c "import mcp_server; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add mcp_server.py
git commit -m "feat: MCP server exposing scan_market tool"
```

---

### Task 11: `README.md` — setup, daily use, Claude Desktop config

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

````markdown
# Claude Stock Screener

Local Python screener for the Nifty universe. Claude calls one tool,
`scan_market`, which fetches all data from Kite + niftyindices and returns only
the qualifying stocks. v1 screens on price (relative strength + SMA); fundamentals
fields are placeholders (null).

## Setup (one time)

1. Create venv and install:
   ```
   py -3.12 -m venv .venv
   .venv/Scripts/python -m pip install -r requirements.txt
   ```
2. Set Kite credentials (PowerShell):
   ```
   setx KITE_API_KEY "your_key"
   setx KITE_API_SECRET "your_secret"
   ```
   Reopen the terminal so they take effect.
3. In developer.kite.trade, set the app **Redirect URL** to
   `http://127.0.0.1:5000/` (enables one-click login).

## Daily use

Each trading morning, mint a token (valid until ~6 AM next day):
```
.venv/Scripts/python login.py
```
A browser opens; log in. The token is saved to `~/.screener/token.json`.

Run a screen from the CLI:
```
.venv/Scripts/python cli.py --universe nifty200 --lookback-days 7
```

## Claude Desktop config

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "screener": {
      "command": "C:/Users/ASUS/Desktop/Claude-Screener/.venv/Scripts/python.exe",
      "args": ["C:/Users/ASUS/Desktop/Claude-Screener/mcp_server.py"],
      "env": {
        "KITE_API_KEY": "your_key",
        "KITE_API_SECRET": "your_secret"
      }
    }
  }
}
```
Restart Claude Desktop. Ask: "Screen Nifty 200 for stocks outperforming NIFTY 50
and their sector over 7 days with SMA20 above SMA50." Claude calls `scan_market`
once.

## Tests
```
.venv/Scripts/python -m pytest -v
```

## Not implemented in v1 (by design)
PE / ROE / ROCE / sector PE (return null). Add a `FundamentalsProvider` to
`screener/fundamentals.py` and wire it in `screen.scan_market` to enable.
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with setup, daily use, and Claude Desktop config"
```

---

### Task 12: End-to-end smoke test (manual, requires live Kite token)

**Files:** none (validation only)

- [ ] **Step 1: Full unit suite green**

Run: `.venv/Scripts/python -m pytest -v`
Expected: all tests PASS.

- [ ] **Step 2: Live login**

Run: `.venv/Scripts/python login.py`
Expected: browser login completes; `~/.screener/token.json` written with today's date.

- [ ] **Step 3: Live CLI run against nifty50 (smaller, faster)**

Run: `.venv/Scripts/python cli.py --universe nifty50 --lookback-days 7`
Expected: valid JSON to stdout with `results`, `warnings`, `meta`; `count` >= 0;
fundamentals fields null; runtime roughly 20-40s.

- [ ] **Step 4: Sanity-check the output**

Confirm: each result has `rs_vs_nifty > 0` and `rs_vs_sector > 0` (default
filters), `sma20 > sma50`, and `meta.universe == "nifty50"`. Spot-check one
symbol's `return7` against a chart.

- [ ] **Step 5: Commit any fixups discovered during smoke test**

```bash
git add -A
git commit -m "fix: smoke-test corrections"
```

---

## Notes for the implementer

- **niftyindices may rate-limit or change CSV headers.** If `fetch_universe`
  returns empty, check the live CSV's header row against `parse_constituents`
  (column names must match exactly: `Symbol`, `Company Name`, `Industry`).
- **Index tradingsymbols** in Kite's NSE dump use names like `NIFTY 50`,
  `NIFTY IT`, `NIFTY FIN SERVICE`. If a needed index isn't found in
  `idx_token`, the sector test falls back to NIFTY 200 (warned). Verify exact
  index names during smoke test and reconcile `sectors.py` if needed
  (e.g. Kite may use `NIFTY FIN SERVICE` rather than `NIFTY FINANCIAL SERVICES`).
- **Token expiry boundary** is handled by `today_trading_date()` (rolls over at
  6 AM IST). A scan before login will raise `KiteAuthError` with the fix command.
```
