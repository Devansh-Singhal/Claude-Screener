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
