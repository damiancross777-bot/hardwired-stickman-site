from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content"
EPISODES_DIR = CONTENT_DIR / "episodes"
SITE_DIR = ROOT / "site"
PUBLIC_DIR = ROOT / "public"
OUTPUT_DIR = ROOT / "output"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_site() -> dict[str, Any]:
    return load_json(CONTENT_DIR / "site.json")


def load_episodes(include_drafts: bool = False) -> list[dict[str, Any]]:
    episodes: list[dict[str, Any]] = []
    for path in sorted(EPISODES_DIR.glob("*.json")):
        episode = load_json(path)
        episode["_source_path"] = str(path)
        if include_drafts or episode.get("status") == "published":
            episodes.append(episode)
    episodes.sort(key=lambda item: item.get("published_at", ""), reverse=True)
    return episodes


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def format_date(value: str) -> str:
    dt = parse_datetime(value)
    # "%-d" (no leading zero) isn't supported by Windows' strftime -- build it manually instead.
    return dt.strftime(f"{dt.day} %B %Y")


def slugify_simple(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        import shutil
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def absolute_url(site_url: str, path: str) -> str:
    return site_url.rstrip("/") + "/" + path.lstrip("/")
