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
