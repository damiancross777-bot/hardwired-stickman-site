"""One-time OAuth authorization for the Pinterest API (v5), Trial access.

Run this once per app registration (or whenever tokens need refreshing from scratch).
It starts a tiny local HTTP server on http://localhost:8888/callback (must exactly
match the Redirect URI registered on the Pinterest app), prints the Pinterest
authorization URL for you to open in your own browser (already logged in as the
hardwiredstickman account), waits for the redirect carrying the authorization code,
exchanges it for an access + refresh token, and saves both to
state/pinterest_tokens.json (gitignored -- never committed).

Requires PINTEREST_APP_ID and PINTEREST_APP_SECRET in offplatform/.env first.
"""
from __future__ import annotations

import base64
import json
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
STATE_DIR = ROOT / "state"
TOKENS_PATH = STATE_DIR / "pinterest_tokens.json"

REDIRECT_URI = "http://localhost:8888/callback"
SCOPES = "boards:read,boards:write,pins:read,pins:write"
AUTH_BASE = "https://www.pinterest.com/oauth/"
TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"


def load_env() -> dict[str, str]:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


_captured: dict[str, str] = {}


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if "code" in qs:
            _captured["code"] = qs["code"][0]
            _captured["state"] = qs.get("state", [""])[0]
            body = b"<html><body><h2>Authorized. You can close this tab and return to the terminal.</h2></body></html>"
        else:
            body = b"<html><body><h2>No authorization code received.</h2></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # quiet
        pass


def main() -> None:
    env = load_env()
    client_id = env.get("PINTEREST_APP_ID")
    client_secret = env.get("PINTEREST_APP_SECRET")
    if not client_id or not client_secret:
        raise SystemExit("Set PINTEREST_APP_ID and PINTEREST_APP_SECRET in offplatform/.env first.")

    state = secrets.token_urlsafe(16)
    auth_url = AUTH_BASE + "?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
    })

    server = HTTPServer(("localhost", 8888), CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    print("\nOpen this URL in your browser (logged in as hardwiredstickman) and click Allow:\n")
    print(auth_url)
    print("\nWaiting for authorization (up to 5 minutes)...")

    thread.join(timeout=300)
    if "code" not in _captured:
        raise SystemExit("Timed out waiting for authorization. Run again.")
    if _captured.get("state") != state:
        raise SystemExit("State mismatch on callback -- possible CSRF, aborting. Run again.")

    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": _captured["code"],
        "redirect_uri": REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST", headers={
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            tokens = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Token exchange failed ({e.code}): {e.read().decode()}")

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    TOKENS_PATH.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    print(f"\nSaved tokens to {TOKENS_PATH} (gitignored). "
          f"Access token expires in {tokens.get('expires_in')}s; refresh_token saved for later use.")


if __name__ == "__main__":
    main()
