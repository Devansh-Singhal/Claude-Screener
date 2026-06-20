# Stock Screener for Claude — Design Spec

**Date:** 2026-06-21
**Status:** Approved design, pre-implementation

## Purpose

A lightweight, personal-use stock-screening service that lets Claude answer
Nifty-universe screening prompts in **exactly one tool call**. All data
collection and computation happen in Python; Claude only interprets the final
filtered JSON.

This replaces the current pattern where Claude itself fan-outs hundreds of
per-stock tool calls (slow, token-heavy, failure-prone).

## Non-goals (explicit scope guardrails)

- **No database** (no SQLite/DuckDB/Postgres/Mongo).
- **No cache** beyond the daily Kite access token. Every run fetches fresh data.
- **No scheduler / cron / background services** (no Redis/Celery/Kafka).
- **No fundamentals implementation in v1** — interface only (see §7).
- Not a trading platform; read-only market data, no order placement.

## v1 scope

Pure **price-based** screening, sourced entirely from Kite (price) + NSE
niftyindices.com (constituents, sector labels):

- 7-day (configurable) return per stock
- Relative strength vs NIFTY 50
- Relative strength vs the stock's NIFTY sectoral index
- SMA(short) vs SMA(long), default SMA20 vs SMA50

Fundamentals filters (`min_roe`, `max_pe`, `min_market_cap`) are **accepted but
no-op**; corresponding output fields (`pe`, `roe`, `roce`, `sector_pe`) return
`null` until a fundamentals provider is plugged in later.

---

## 1. Architecture

One core library; two thin adapters. All logic is in `screener/`, fully
testable without live network calls. `cli.py` and `mcp_server.py` are ~30-line
wrappers.

```
Claude-Screener/
  screener/                  # core library
    config.py                # paths, constants, Kite creds from env
    kite_client.py           # auth + concurrent historical fetch
    universe.py              # NIFTY constituents + Industry labels (niftyindices)
    sectors.py               # Industry -> NIFTY sectoral index map + index series
    indicators.py            # SMA, N-day return, relative strength (pandas)
    fundamentals.py          # Provider ABC + NullProvider (placeholder)
    screen.py                # scan_market() orchestration
  cli.py                     # argparse -> prints JSON   (manual testing)
  mcp_server.py              # exposes one tool: scan_market   (Claude Desktop)
  login.py                   # daily Kite token helper (autograb)
  tests/                     # pytest
  requirements.txt
  README.md
  docs/superpowers/specs/    # this document
```

**Why this shape:** "Both CLI and MCP" costs almost nothing because the hard
logic is written and tested once in the library; the adapters just marshal
arguments and serialize JSON. The latency win over Claude-driven screening
comes from running the fan-out as one concurrent Python process.

## 2. `scan_market` interface

```python
scan_market(
    universe="nifty200",              # "nifty50" | "nifty200" | "nifty500"
    benchmark="NIFTY 50",
    lookback_days=7,                  # relative-strength window
    sma_short=20,
    sma_long=50,
    require_outperform_benchmark=True,
    require_outperform_sector=True,
    require_sma_bullish=True,         # sma_short > sma_long
    min_roe=None,                     # accepted, NO-OP in v1
    max_pe=None,                      # accepted, NO-OP in v1
    min_market_cap=None,              # accepted, NO-OP in v1
    sort_by="rs_vs_nifty",            # "rs_vs_nifty" | "rs_vs_sector" | "return7"
) -> dict
```

Each boolean `require_*` flag is an AND filter. A stock is returned only if it
passes every enabled filter. Disabling a flag drops that condition.

## 3. Data flow (single call)

1. **Universe** — download the constituent CSV for the chosen universe from
   niftyindices.com (live). Parse `Symbol`, `Company Name`, `Industry`.
2. **Instrument tokens** — download Kite's instrument dump once; resolve each
   NSE symbol to its `instrument_token`.
3. **Sector resolution** — map each stock's `Industry` to its NIFTY sectoral
   index (see §4). Collect the unique set of sector indices needed.
4. **Concurrent fetch** — pull daily candles for `lookback + max(sma_long) +
   buffer` (~80 trading days) for: all universe stocks + NIFTY 50 + each needed
   sector index. Uses `ThreadPoolExecutor` throttled to Kite's historical-data
   limit of **3 requests/second**.
5. **Indicators** — per stock compute `sma_short`, `sma_long`, `return7`; per
   benchmark compute `nifty_return7`, `sector_return7`.
6. **Relative strength** — `rs_vs_nifty = return7 - nifty_return7`;
   `rs_vs_sector = return7 - sector_return7`.
7. **Filter + sort** — apply enabled `require_*` flags, sort by `sort_by`.
8. **Return** JSON (see §5).

## 4. Sector mapping

The niftyindices constituent CSV includes an `Industry` column (e.g.
"Information Technology", "Financial Services"). `sectors.py` holds a static
`Industry -> NIFTY sectoral index` map, e.g.:

| Industry | NIFTY sectoral index |
|---|---|
| Information Technology | NIFTY IT |
| Financial Services | NIFTY FINANCIAL SERVICES |
| Fast Moving Consumer Goods | NIFTY FMCG |
| Automobile and Auto Components | NIFTY AUTO |
| Healthcare | NIFTY PHARMA |
| Metals & Mining | NIFTY METAL |
| Oil Gas & Consumable Fuels | NIFTY OIL & GAS |
| Power | NIFTY ENERGY |
| ... | ... |

- An Industry with **no matching sectoral index** falls back to using NIFTY 200
  as the sector benchmark; this is recorded in `warnings`.
- This same NIFTY-sectoral-index basis is what a future sector-PE source
  (niftyindices PE/PB feed) will align with.

## 5. Output

```json
{
  "results": [
    {
      "symbol": "TCS",
      "company": "Tata Consultancy Services Ltd.",
      "sector": "Information Technology",
      "pe": null,
      "sector_pe": null,
      "roe": null,
      "roce": null,
      "sma20": 3812.4,
      "sma50": 3760.1,
      "return7": 4.21,
      "nifty_return7": 1.05,
      "sector_return7": 2.30,
      "rs_vs_nifty": 3.16,
      "rs_vs_sector": 1.91
    }
  ],
  "warnings": [
    "POWERGRID: no sectoral index for Industry 'Power' mapped -> fell back to NIFTY 200",
    "XYZ: historical fetch failed, skipped"
  ],
  "meta": {
    "universe": "nifty200",
    "lookback_days": 7,
    "as_of": "2026-06-21",
    "count": 1
  }
}
```

Returns are expressed as percentages. `null` fundamentals fields are
placeholders for the future provider.

## 6. Kite authentication

Kite Connect requires an interactive login that yields an `access_token` valid
until ~6 AM IST the next day. No refresh token exists. The tool therefore needs
a once-daily human login.

- **`login.py` (autograb, default):** briefly starts a local one-request HTTP
  server on `http://127.0.0.1:5000/`, opens `kite.login_url()` in the browser,
  catches the redirect carrying `request_token`, exchanges it via
  `generate_session(request_token, api_secret)`, and writes
  `~/.screener/token.json` = `{ "access_token": ..., "date": "YYYY-MM-DD" }`.
  The server handles exactly one request then stops. No standing service.
  - **One-time setup:** set the Kite app's Redirect URL to
    `http://127.0.0.1:5000/` in developer.kite.trade.
  - **Fallback (paste flow):** if autograb can't bind/redirect, `login.py`
    prints the login URL and prompts the user to paste the `request_token` from
    the browser address bar.
- **`kite_client.py`:** on each scan, loads `~/.screener/token.json`. If missing
  or `date != today`, raises `KiteAuthError("Token missing or stale. Run: python
  login.py")`. Otherwise `kite.set_access_token(...)` and proceed.

Credentials: `KITE_API_KEY` and `KITE_API_SECRET` read from environment
(documented in README; never committed).

## 7. Fundamentals interface (placeholder)

```python
class FundamentalsProvider(ABC):
    @abstractmethod
    def get(self, symbols: list[str]) -> dict[str, dict]:
        """symbol -> {"pe": float|None, "roe": float|None,
                      "roce": float|None, "market_cap": float|None}"""

class NullProvider(FundamentalsProvider):
    def get(self, symbols): return {s: {} for s in symbols}
```

`screen.py` always calls the configured provider (default `NullProvider`) and
merges results; missing keys serialize as `null`. A future FMP/yfinance provider
implements the same `get()` and the fundamentals filters activate with no change
to screening logic. Sector PE (a future niftyindices PE feed) attaches to the
sector record, also via this seam.

## 8. Error handling

- Stale/missing token -> explicit actionable `KiteAuthError`, never a mid-scan
  stack trace.
- Per-symbol fetch failure -> skip the symbol, record in `warnings`, continue.
  One bad symbol never fails the whole scan.
- Industry with no sectoral index -> sector test falls back to NIFTY 200, noted
  in `warnings`.
- niftyindices CSV download failure -> hard error (universe is essential).

## 9. Concurrency & rate limits

- `kiteconnect` is synchronous (requests-based) -> use `ThreadPoolExecutor`.
- Kite historical-data limit is **3 requests/second**. A token-bucket / small
  worker pool (<=3 concurrent + pacing) keeps within limits. ~200 stocks plus a
  handful of indices completes in roughly a minute.

## 10. Testing strategy

- **TDD** on `indicators.py`: SMA, N-day return, and relative strength verified
  against hand-computed values on synthetic series.
- `universe.py` / `sectors.py`: parsed against committed fixture CSVs (no live
  calls); Industry->index map has a coverage test over the full Nifty-200
  Industry set.
- `screen.py`: orchestration tested with a **mock Kite client** returning canned
  candles — verifies filtering, sorting, warnings, null fundamentals.
- Live Kite calls are **not** in the unit suite. One manual `cli.py` smoke run
  validates end-to-end against the real API.

## 11. Dependencies

- `kiteconnect` — official Kite SDK
- `pandas` — indicator math
- `requests` — niftyindices CSV download
- `mcp` — MCP server SDK (Python)
- `pytest` — tests

## Open items deferred to future versions

- Real fundamentals provider (FMP recommended; yfinance free fallback).
- Sector PE feed from niftyindices PE/PB data.
- Optional full TOTP auto-login (deliberately excluded: stores sensitive
  credentials, ToS grey area).
