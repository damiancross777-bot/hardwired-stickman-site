"""Create ONE test pin via the Pinterest API v5, using Trial access.

Trial-tier pins are visible only to the authenticated (creator) account, not the
public -- this validates the OAuth + create-pin flow works end-to-end without
needing to wait for Standard/public access approval.

Requires state/pinterest_tokens.json (run pinterest_oauth.py first).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS_PATH = ROOT / "state" / "pinterest_tokens.json"

API_BASE = "https://api.pinterest.com/v5"
TEST_BOARD_NAME = "Human Behaviour Explained"
TEST_IMAGE_URL = "https://hardwiredstickman.com/social/why-do-babies-smile/pinterest/pin-01.jpg"
TEST_PIN_TITLE = "Why Do Babies Smile Before They Can See Your Face?"
TEST_PIN_DESCRIPTION = (
    "A newborn's vision is close to the clinical threshold for legal blindness -- "
    "so how is it already smiling straight at your face within weeks? "
    "[TEST PIN -- Trial access, visible only to this account]"
)
TEST_PIN_LINK = "https://hardwiredstickman.com/episodes/why-do-babies-smile/"


def load_tokens() -> dict:
    if not TOKENS_PATH.exists():
        raise SystemExit(f"No tokens found at {TOKENS_PATH} -- run pinterest_oauth.py first.")
    return json.loads(TOKENS_PATH.read_text(encoding="utf-8"))


def api_call(method: str, path: str, token: str, payload: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} failed ({e.code}): {e.read().decode()}")


def find_or_create_board(token: str) -> str:
    boards = api_call("GET", "/boards", token)
    for b in boards.get("items", []):
        if b.get("name") == TEST_BOARD_NAME:
            print(f"Using existing board: {b['name']} ({b['id']})")
            return b["id"]
    created = api_call("POST", "/boards", token, {
        "name": TEST_BOARD_NAME,
        "description": "Research-backed explainers about human behaviour.",
        "privacy": "PUBLIC",
    })
    print(f"Created board: {created['name']} ({created['id']})")
    return created["id"]


def main() -> None:
    tokens = load_tokens()
    access_token = tokens["access_token"]

    board_id = find_or_create_board(access_token)

    pin = api_call("POST", "/pins", access_token, {
        "board_id": board_id,
        "title": TEST_PIN_TITLE,
        "description": TEST_PIN_DESCRIPTION,
        "link": TEST_PIN_LINK,
        "media_source": {
            "source_type": "image_url",
            "url": TEST_IMAGE_URL,
        },
    })
    print(f"\nCreated pin: {pin.get('id')}")
    print(f"View at: https://www.pinterest.com/pin/{pin.get('id')}/")
    print("(Trial access -- this pin is visible only to your own account, not the public.)")


if __name__ == "__main__":
    main()
