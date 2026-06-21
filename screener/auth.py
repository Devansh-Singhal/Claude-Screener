"""Kite login that works from a chat link (no terminal needed).

`start_login_capture()` returns the Kite login URL and starts a one-shot local
listener on REDIRECT_PORT in a background thread. When the user opens the URL,
logs in, and Zerodha redirects to http://127.0.0.1:5000/, the listener exchanges
the request_token for an access token and saves it to TOKEN_PATH. This mirrors
how the hosted Kite MCP hands you a login link.
"""
import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from kiteconnect import KiteConnect

from . import config
from .kite_client import today_trading_date


def _save_token(access_token: str) -> None:
    config.TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.TOKEN_PATH.write_text(json.dumps({
        "access_token": access_token,
        "date": today_trading_date(),
    }))


def _make_handler(kite: KiteConnect, api_secret: str):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.urlparse(self.path).query
            request_token = urllib.parse.parse_qs(query).get("request_token", [None])[0]
            if request_token:
                try:
                    data = kite.generate_session(request_token, api_secret=api_secret)
                    _save_token(data["access_token"])
                    msg = "Login successful. Close this tab and return to Claude."
                except Exception as e:  # surfaced in the browser, not crashed
                    msg = f"Login failed: {e}"
            else:
                msg = "No request_token in the redirect. Check the app Redirect URL."
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html><body><h3>{msg}</h3></body></html>".encode())

        def log_message(self, *a):  # silence server logs
            pass

    return Handler


def start_login_capture() -> str:
    """Return the Kite login URL and start capturing the redirect in the
    background. The user opens the URL; the token is saved automatically on
    successful login."""
    kite = KiteConnect(api_key=config.api_key())
    api_secret = config.api_secret()
    try:
        server = HTTPServer(("127.0.0.1", config.REDIRECT_PORT),
                            _make_handler(kite, api_secret))
        threading.Thread(target=server.handle_request, daemon=True).start()
    except OSError:
        # A listener from a prior, still-pending login is already waiting on the
        # port; it will capture this login too. Just hand back the URL.
        pass
    return kite.login_url()
