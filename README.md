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

Each trading morning, mint a Kite token (valid until ~6 AM IST next day). Two ways:

- **From Claude (recommended):** ask Claude to log in. It calls the `kite_login`
  tool, which returns a login URL — open it, log in to Zerodha, and the token is
  captured and saved automatically. `kite_login_status` confirms you're logged in.
- **From a terminal:** `.venv/Scripts/python login.py` — a browser opens; log in.

Either way the token is saved to `~/.screener/token.json`.

Run a screen from the CLI:
```
.venv/Scripts/python cli.py --universe nifty200 --lookback-days 7
```

## Supertrend

Every result reports Supertrend (ATR period 10, multiplier 3.0, Wilder's ATR —
the chart defaults): `supertrend` (+1 up / -1 down), `supertrend_signal`
("buy"/"sell"/null on a fresh flip this candle), and `supertrend_value` (the
line). Add `require_supertrend_bullish` (CLI: `--supertrend-bullish`) to keep
only stocks currently in a Supertrend uptrend. Tune with `supertrend_period` /
`supertrend_multiplier`. Ask Claude e.g. "...and only those with a bullish
Supertrend."

## TradingView watchlist export (on demand)

Turn results into a TradingView-importable file when you ask. In Claude, after a
scan: "export those to a TradingView watchlist" — Claude calls the
`export_watchlist` tool, which writes `output/watchlist_<timestamp>.txt`
(exchange-prefixed, comma-separated, e.g. `NSE:TRENT,NSE:INDIGO`). From the CLI:
`.venv/Scripts/python cli.py --universe nifty50 --watchlist`. Import in
TradingView via the Watchlist menu -> Import.

## Output

Every scan is saved to `output/scan_<universe>_<timestamp>.json` (kept, never
auto-deleted; the folder is gitignored). The same JSON is also returned to the
caller, and its path appears in `meta.saved_to`.

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
Restart Claude Desktop. Tools exposed: `kite_login`, `kite_login_status`, and
`scan_market`. Ask Claude to log in (once per day), then: "Screen Nifty 200 for
stocks outperforming NIFTY 50 and their sector over 7 days with SMA20 above
SMA50." Claude calls `scan_market` once.

## Tests
```
.venv/Scripts/python -m pytest -v
```

## Not implemented in v1 (by design)
PE / ROE / ROCE / sector PE (return null). Add a `FundamentalsProvider` to
`screener/fundamentals.py` and wire it in `screen.scan_market` to enable.
