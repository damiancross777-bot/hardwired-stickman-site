from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from common import EPISODES_DIR, slugify_simple


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new Hardwired Stickman episode file.")
    parser.add_argument("title")
    parser.add_argument("--category", default="Human Behaviour")
    args = parser.parse_args()

    slug = slugify_simple(args.title)
    destination = EPISODES_DIR / f"{slug}.json"
    if destination.exists():
        raise SystemExit(f"Episode already exists: {destination}")

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    data = {
        "title": args.title,
        "slug": slug,
        "status": "draft",
        "published_at": now,
        "updated_at": now,
        "category": args.category,
        "summary": "Replace with a concise summary.",
        "answer": "Replace with a direct one-paragraph answer.",
        "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
        "youtube_id": "VIDEO_ID",
        "duration_iso": "PT8M00S",
        "thumbnail_url": "https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg",
        "key_findings": [
            "First verified finding.",
            "Second verified finding.",
            "Third verified finding."
        ],
        "article_markdown": "## The question\n\nWrite the article here.",
        "sources": [
            {
                "title": "Replace with source title",
                "publisher": "Replace with publisher",
                "url": "https://example.com/replace-this-source"
            }
        ],
        "related_slugs": [],
        "seo": {
            "title": f"{args.title} | Hardwired Stickman",
            "description": "Replace with a search description.",
            "keywords": []
        },
        "pinterest": {
            "board": f"{args.category} Explained",
            "hooks": [
                args.title,
                "Second Pinterest hook",
                "Third Pinterest hook"
            ],
            "description": "Replace with a Pinterest description."
        },
        "instagram": {
            "caption": "Replace with an Instagram caption.",
            "hashtags": ["hardwiredstickman"],
            "slides": [
                {"heading": args.title, "body": "The core question."},
                {"heading": "THE OBVIOUS EXPLANATION", "body": "What people usually assume."},
                {"heading": "WHAT RESEARCHERS FOUND", "body": "The strongest finding."},
                {"heading": "WHY IT EXISTS", "body": "The behavioural mechanism."},
                {"heading": "A SURPRISING EXAMPLE", "body": "A memorable case."},
                {"heading": "THE TAKEAWAY", "body": "The practical implication."},
                {"heading": "WATCH THE FULL EXPLANATION", "body": "Hardwired Stickman."}
            ]
        },
        "reel": {
            "hook": "Replace with a sharp opening line.",
            "beats": ["Beat one.", "Beat two.", "Beat three.", "Beat four."],
            "cta": "Watch the full Hardwired Stickman episode."
        }
    }

    destination.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
