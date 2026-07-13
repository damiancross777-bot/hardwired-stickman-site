from __future__ import annotations

import sys
from urllib.parse import urlparse

from common import load_episodes, load_site, parse_datetime

REQUIRED_EPISODE_FIELDS = [
    "title", "slug", "status", "published_at", "category", "summary",
    "answer", "youtube_url", "key_findings", "article_markdown",
    "sources", "seo", "pinterest", "instagram"
]


def valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    site = load_site()

    for field in ["site_name", "tagline", "description", "site_url", "language"]:
        if not site.get(field):
            errors.append(f"site.json: missing '{field}'")

    episodes = load_episodes(include_drafts=True)
    slugs: set[str] = set()

    for episode in episodes:
        source = episode["_source_path"]
        for field in REQUIRED_EPISODE_FIELDS:
            if field not in episode or episode[field] in (None, "", [], {}):
                errors.append(f"{source}: missing or empty '{field}'")

        slug = episode.get("slug", "")
        if slug in slugs:
            errors.append(f"{source}: duplicate slug '{slug}'")
        slugs.add(slug)

        try:
            parse_datetime(episode.get("published_at", ""))
        except Exception:
            errors.append(f"{source}: invalid ISO datetime in 'published_at'")

        if len(episode.get("key_findings", [])) < 3:
            warnings.append(f"{source}: fewer than three key findings")

        if not valid_url(episode.get("youtube_url", "")):
            errors.append(f"{source}: invalid youtube_url")

        for source_item in episode.get("sources", []):
            url = source_item.get("url", "")
            if not valid_url(url):
                errors.append(f"{source}: invalid source URL '{url}'")
            if "example.com" in url or "replace-this" in url:
                warnings.append(f"{source}: placeholder source remains: {url}")

        hooks = episode.get("pinterest", {}).get("hooks", [])
        if len(hooks) < 3:
            warnings.append(f"{source}: add at least three Pinterest hooks")

        slides = episode.get("instagram", {}).get("slides", [])
        if len(slides) != 7:
            warnings.append(f"{source}: Instagram carousel works best with exactly seven slides")

    for warning in warnings:
        print(f"WARNING: {warning}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"\nValidation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    print(f"Validation passed: {len(episodes)} episode file(s), {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
