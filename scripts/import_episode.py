"""Draft an off-platform episode JSON from Hardwired_Stickman production data.

Reads ../episodes/<episode-dir>/{episode.json, metadata.txt, sources.json, script.md}
from the video-production pipeline and writes content/episodes/<slug>.json with
everything the pipeline already knows filled in (title, category, SEO description,
tags/hashtags, sources, candidate key findings).

Fields the production pipeline has no equivalent for -- article_markdown (a fresh
long-form written article, not the spoken script verbatim), Pinterest hooks/board
description, Instagram carousel slides/caption, and the Reel brief -- are left as
"TODO" placeholders. This script never invents that content; it only imports what
already exists and cleared the CLAUDE.md Sec 5 sourcing gate.

Usage:
    python scripts/import_episode.py 001
    python scripts/import_episode.py 001-why-do-babies-smile --force
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

OFFPLATFORM_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ROOT = OFFPLATFORM_ROOT.parent
EPISODES_DIR = PRODUCTION_ROOT / "episodes"
OUT_DIR = OFFPLATFORM_ROOT / "content" / "episodes"

LANE_TO_CATEGORY = {
    "human_psychology": "Human Behaviour",
    "animal_behavior": "Animal Behaviour",
    "animal_cognition": "Animal Behaviour",
}
# lanes with no clean 1:1 category mapping -- default applied, always flagged for manual confirm
LANE_CATEGORY_FALLBACK = "Human Behaviour"

TODO = "TODO -- fill in before publish"


def find_episode_dir(identifier: str) -> Path:
    direct = EPISODES_DIR / identifier
    if direct.is_dir():
        return direct
    matches = sorted(p for p in EPISODES_DIR.iterdir() if p.is_dir() and p.name.startswith(identifier))
    if not matches:
        raise SystemExit(f"No episode folder found matching '{identifier}' in {EPISODES_DIR}")
    if len(matches) > 1:
        raise SystemExit(f"Ambiguous identifier '{identifier}', matches: {[m.name for m in matches]}")
    return matches[0]


def parse_metadata_txt(path: Path) -> dict[str, str]:
    """Parse step_metadata.py's fixed '--- SECTION NAME ---' format.
    Section headers occasionally wrap across two lines (e.g. CHAPTERS), so this
    splits on lines starting a new '--- ' block rather than assuming one line."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n(?=--- )", text)
    sections: dict[str, str] = {}
    for block in blocks:
        m = re.match(r"---\s*(.+?)\s*---\s*\n?(.*)", block, flags=re.DOTALL)
        if not m:
            continue
        header = re.sub(r"\s+", " ", m.group(1)).strip()
        sections[header] = m.group(2).strip()
    return sections


def get_section(sections: dict[str, str], keyword: str) -> str:
    for name, body in sections.items():
        if name.upper().startswith(keyword.upper()):
            return body
    return ""


def first_title_option(section_text: str) -> str:
    m = re.search(r"^1\.\s+(.+?)\s{2,}\[\d+ chars\]\s*$", section_text, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()
    for line in section_text.splitlines():
        line = line.strip()
        if line:
            line = re.sub(r"^\d+\.\s*", "", line)
            return re.sub(r"\s*\[\d+ chars\]\s*$", "", line)
    return ""


def parse_description_block(section_text: str) -> tuple[str, str]:
    """Returns (seo_description_line, full_body_without_sources)."""
    body = section_text.split("Sources & further reading")[0]
    body = body.rstrip("-— \n\t")
    lines = [l for l in body.splitlines() if l.strip()]
    seo_line = lines[0].strip() if lines else ""
    return seo_line, body.strip()


def parse_tags(section_text: str) -> list[str]:
    return [t.strip() for t in section_text.split(",") if t.strip()]


def parse_hashtags(section_text: str) -> list[str]:
    return [t.lstrip("#").strip() for t in section_text.split() if t.startswith("#")]


def load_sources_json(path: Path) -> tuple[list[dict], int]:
    """Normalize both the established 001-010 schema (concept/citation/type/year/
    url/hedge) and the 011-020 schema (claim/authors/year/publication/citation/url/
    verified) into the off-platform site's {title, publisher, url} shape.
    Returns (sources, skipped_count) -- entries with no real URL (e.g. a general
    "research pushback, not attributed to one researcher" caveat) can't be a
    clickable on-site citation, so they're dropped rather than shipped broken."""
    if not path.exists():
        return [], 0
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    skipped = 0
    for s in data.get("sources", []):
        citation = s.get("citation", "")
        claim = s.get("concept") or s.get("claim") or ""
        url = s.get("url", "")
        if not url:
            skipped += 1
            continue
        title = citation or claim or "Untitled source"
        out.append({"title": title, "publisher": claim if citation else "", "url": url})
    return out, skipped


def extract_key_findings(script_md_path: Path, max_items: int = 5) -> list[str]:
    """Naive pull of candidate one-liners out of Beat 4 (sub-mechanisms).
    Always needs a human pick/trim pass -- this is a starting shortlist, not final copy."""
    if not script_md_path.exists():
        return []
    text = script_md_path.read_text(encoding="utf-8")
    m = re.search(r"## BEAT 4.*?\n(.*?)(?=\n## BEAT|\Z)", text, flags=re.DOTALL)
    if not m:
        return []
    paragraphs = [p.strip().replace("\n", " ") for p in m.group(1).split("\n\n")
                  if p.strip() and not p.strip().startswith("---")]
    findings = []
    for p in paragraphs:
        sentences = re.split(r"(?<=[.?!])\s+", p)
        if sentences and sentences[0]:
            findings.append(sentences[0])
        if len(findings) >= max_items:
            break
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("episode", help="Episode folder name or leading number, e.g. '001' or '001-why-do-babies-smile'")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing draft JSON")
    args = parser.parse_args()

    ep_dir = find_episode_dir(args.episode)
    print(f"Reading production data from: {ep_dir}")

    episode_json = json.loads((ep_dir / "episode.json").read_text(encoding="utf-8"))
    metadata_sections = parse_metadata_txt(ep_dir / "metadata.txt")
    if not metadata_sections:
        print("NOTE: no metadata.txt found (run step_metadata.py first for richer SEO/tags data) -- continuing with episode.json/sources.json/script.md only.")
    sources, skipped_sources = load_sources_json(ep_dir / "sources.json")
    if skipped_sources:
        print(f"NOTE: skipped {skipped_sources} source(s) with no URL (general caveats, not pinned citations) -- not linkable on-site.")
    key_findings = extract_key_findings(ep_dir / "script.md")

    slug = episode_json.get("slug") or re.sub(r"^\d+[-_]?", "", ep_dir.name).lower()
    title = episode_json.get("title", "")
    title_section = get_section(metadata_sections, "TITLE OPTIONS")
    if title_section:
        picked = first_title_option(title_section)
        if picked:
            title = picked

    lane = episode_json.get("lane", "")
    category = LANE_TO_CATEGORY.get(lane, LANE_CATEGORY_FALLBACK)
    if lane not in LANE_TO_CATEGORY:
        print(f"WARNING: lane '{lane}' has no clean category mapping -- defaulted to '{category}', confirm manually.")

    description_section = get_section(metadata_sections, "DESCRIPTION")
    seo_description, description_body = parse_description_block(description_section) if description_section else ("", "")

    tags = parse_tags(get_section(metadata_sections, "TAGS"))
    hashtags = parse_hashtags(get_section(metadata_sections, "HASHTAGS"))

    draft = {
        "title": title,
        "slug": slug,
        "status": "draft",
        "published_at": f"{TODO} -- ISO datetime, set on actual publish",
        "updated_at": f"{TODO} -- ISO datetime",
        "category": category,
        "summary": seo_description or TODO,
        "answer": f"{TODO} -- one paragraph direct answer; can adapt from script.md's cold open / closing reframe",
        "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
        "youtube_id": "VIDEO_ID",
        "duration_iso": f"{TODO} -- e.g. PT8M30S, fill in once the final render duration is known",
        "thumbnail_url": "https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg",
        "key_findings": key_findings if len(key_findings) >= 3 else key_findings + [TODO] * (3 - len(key_findings)),
        "article_markdown": f"{TODO} -- fresh long-form written article for reading (NOT the spoken script verbatim). Use script.md and sources.json as source material.",
        "sources": sources or [{"title": TODO, "publisher": "", "url": ""}],
        "related_slugs": [],
        "seo": {
            "title": f"{title} | Hardwired Stickman" if title else TODO,
            "description": seo_description or TODO,
            "keywords": tags or [TODO],
        },
        "pinterest": {
            "board": f"{category} Explained",
            "hooks": [TODO, TODO, TODO],
            "description": TODO,
        },
        "instagram": {
            "caption": TODO,
            "hashtags": hashtags or [TODO],
            "slides": [{"heading": TODO, "body": TODO} for _ in range(7)],
        },
        "reel": {
            "hook": TODO,
            "beats": [TODO, TODO, TODO, TODO],
            "cta": "Watch the full Hardwired Stickman episode.",
        },
        "_source": {
            "episode_dir": ep_dir.name,
            "generated_by": "offplatform/scripts/import_episode.py",
            "note": ("Auto-filled from the production pipeline: title, category, summary/seo.description, "
                      "sources, seo.keywords, instagram.hashtags, key_findings (shortlist, needs a trim pass). "
                      f"Every field still containing '{TODO}' needs manual or Claude-assisted drafting."),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{slug}.json"
    if out_path.exists() and not args.force:
        raise SystemExit(f"{out_path} already exists. Use --force to overwrite.")
    out_path.write_text(json.dumps(draft, indent=2, ensure_ascii=False), encoding="utf-8")

    todo_count = json.dumps(draft).count("TODO")
    print(f"Wrote draft: {out_path}")
    print(f"Auto-filled: title, category, {len(sources)} source(s), {len(tags)} SEO keyword(s), "
          f"{len(hashtags)} hashtag(s), {len(key_findings)} candidate key finding(s).")
    print(f"Remaining manual fields ({todo_count} TODO marker(s)): article_markdown, pinterest hooks/description, "
          f"instagram slides/caption, reel, youtube_url/id/thumbnail (once video is live), duration_iso, "
          f"published_at/updated_at, answer.")


if __name__ == "__main__":
    main()
