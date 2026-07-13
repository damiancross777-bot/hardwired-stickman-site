from __future__ import annotations

import csv
import json
import math
import shutil
import textwrap
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from common import OUTPUT_DIR, absolute_url, ensure_clean_dir, load_episodes, load_site

FONT_BOLD_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
FONT_REGULAR_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def find_font(candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


FONT_BOLD = find_font(FONT_BOLD_CANDIDATES)
FONT_REGULAR = find_font(FONT_REGULAR_CANDIDATES)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    if path:
        return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int,
             min_size: int, bold: bool = True) -> tuple[ImageFont.ImageFont, list[str]]:
    for size in range(start_size, min_size - 1, -2):
        f = font(size, bold)
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), candidate, font=f)
            if bbox[2] - bbox[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if len(lines) <= 5:
            return f, lines
    return font(min_size, bold), textwrap.wrap(text, width=20)


def draw_stickman(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float,
                  colour: tuple[int, int, int], accent: tuple[int, int, int]) -> None:
    width = max(4, int(8 * scale))
    head_r = int(52 * scale)
    draw.ellipse((cx-head_r, cy-head_r, cx+head_r, cy+head_r), outline=colour, width=width)
    neck_y = cy + head_r
    hip_y = neck_y + int(180 * scale)
    draw.line((cx, neck_y, cx, hip_y), fill=colour, width=width)
    draw.line((cx, neck_y + int(55*scale), cx-int(110*scale), neck_y+int(120*scale)),
              fill=colour, width=width)
    draw.line((cx, neck_y + int(55*scale), cx+int(110*scale), neck_y+int(95*scale)),
              fill=colour, width=width)
    draw.line((cx, hip_y, cx-int(95*scale), hip_y+int(150*scale)), fill=colour, width=width)
    draw.line((cx, hip_y, cx+int(95*scale), hip_y+int(150*scale)), fill=colour, width=width)
    # "Hardwired" circuit nodes
    draw.line((cx-head_r//2, cy, cx+head_r//2, cy), fill=accent, width=max(3, width//2))
    for dx in (-head_r//2, 0, head_r//2):
        r = max(5, int(8*scale))
        draw.ellipse((cx+dx-r, cy-r, cx+dx+r, cy+r), fill=accent)


def add_brand(draw: ImageDraw.ImageDraw, width: int, height: int, site: dict) -> None:
    accent = hex_rgb(site["brand"]["accent"])
    muted = hex_rgb(site["brand"]["muted"])
    draw.rectangle((0, 0, width, 16), fill=accent)
    draw.text((70, height-100), site["site_name"].upper(), font=font(35, True), fill=muted)


def draw_wrapped(draw: ImageDraw.ImageDraw, lines: list[str], xy: tuple[int, int],
                 f: ImageFont.ImageFont, fill, spacing: int = 12) -> int:
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=f, fill=fill)
        bbox = draw.textbbox((x, y), line, font=f)
        y += (bbox[3] - bbox[1]) + spacing
    return y


def create_pin(site: dict, episode: dict, hook: str, number: int, out_dir: Path) -> Path:
    width, height = 1000, 1500
    bg = hex_rgb(site["brand"]["background"])
    surface = hex_rgb(site["brand"]["surface"])
    paper = hex_rgb(site["brand"]["paper"])
    accent = hex_rgb(site["brand"]["accent"])
    accent2 = hex_rgb(site["brand"]["accent_2"])
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((50, 50, width-50, height-50), radius=40, fill=surface, outline=accent, width=4)
    draw.rectangle((50, 50, width-50, 84), fill=accent)
    draw.text((90, 115), episode["category"].upper(), font=font(34, True), fill=accent)

    title_font, lines = fit_text(draw, hook.upper(), 820, 95, 58, True)
    y = draw_wrapped(draw, lines, (90, 235), title_font, paper, 16)

    draw_stickman(draw, 500, max(780, y+235), 0.78, paper, accent2)

    answer = episode["answer"]
    body_font, body_lines = fit_text(draw, answer, 820, 35, 27, False)
    draw_wrapped(draw, body_lines[:5], (90, 1115), body_font, paper, 10)

    add_brand(draw, width, height, site)
    output = out_dir / f"pin-{number:02d}.jpg"
    image.save(output, quality=92, optimize=True)
    return output


def create_instagram_slide(site: dict, episode: dict, slide: dict, number: int, out_dir: Path) -> Path:
    width, height = 1080, 1350
    bg = hex_rgb(site["brand"]["background"])
    surface = hex_rgb(site["brand"]["surface"])
    paper = hex_rgb(site["brand"]["paper"])
    accent = hex_rgb(site["brand"]["accent"])
    accent2 = hex_rgb(site["brand"]["accent_2"])
    muted = hex_rgb(site["brand"]["muted"])

    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((55, 55, width-55, height-55), radius=42, fill=surface)
    draw.text((90, 85), f"{number:02d} / 07", font=font(30, True), fill=accent)

    title_font, title_lines = fit_text(draw, slide["heading"].upper(), 880, 74, 48, True)
    y = draw_wrapped(draw, title_lines, (90, 190), title_font, paper, 14)

    draw.line((90, y+35, 430, y+35), fill=accent2, width=9)
    body_font, body_lines = fit_text(draw, slide["body"], 860, 42, 30, False)
    draw_wrapped(draw, body_lines, (90, y+90), body_font, muted, 14)

    draw_stickman(draw, 540, 845, 0.80, paper, accent)
    add_brand(draw, width, height, site)

    output = out_dir / f"slide-{number:02d}.jpg"
    image.save(output, quality=92, optimize=True)
    return output


def main() -> None:
    site = load_site()
    episodes = load_episodes()
    social_root = OUTPUT_DIR / "social"
    ensure_clean_dir(social_root)

    csv_rows = []
    for episode in episodes:
        episode_root = social_root / episode["slug"]
        pin_dir = episode_root / "pinterest"
        ig_dir = episode_root / "instagram"
        pin_dir.mkdir(parents=True, exist_ok=True)
        ig_dir.mkdir(parents=True, exist_ok=True)

        hooks = episode["pinterest"]["hooks"][:3]
        for index, hook in enumerate(hooks, start=1):
            path = create_pin(site, episode, hook, index, pin_dir)
            public_media_url = absolute_url(
                site["site_url"],
                f"social/{episode['slug']}/pinterest/{path.name}"
            )
            csv_rows.append({
                "Title": hook,
                "Media URL": public_media_url,
                "Pinterest board": episode["pinterest"].get("board", site["default_board"]),
                "Description": episode["pinterest"]["description"],
                "Link": absolute_url(site["site_url"], f"episodes/{episode['slug']}/"),
                "Publish date": "",
                "Keywords": ", ".join(episode["seo"].get("keywords", [])),
            })

        for index, slide in enumerate(episode["instagram"]["slides"][:7], start=1):
            create_instagram_slide(site, episode, slide, index, ig_dir)

        caption = episode["instagram"]["caption"].rstrip()
        hashtags = " ".join(f"#{tag.lstrip('#')}" for tag in episode["instagram"].get("hashtags", []))
        (ig_dir / "caption.txt").write_text(f"{caption}\n\n{hashtags}\n", encoding="utf-8")

        reel = episode.get("reel", {})
        reel_text = [reel.get("hook", ""), ""]
        for i, beat in enumerate(reel.get("beats", []), start=1):
            reel_text.append(f"{i}. {beat}")
        reel_text += ["", reel.get("cta", "")]
        (episode_root / "reel-brief.txt").write_text("\n".join(reel_text), encoding="utf-8")

        manifest = {
            "episode": episode["title"],
            "landing_page": absolute_url(site["site_url"], f"episodes/{episode['slug']}/"),
            "pinterest_files": [f"pinterest/pin-{i:02d}.jpg" for i in range(1, len(hooks)+1)],
            "instagram_files": [f"instagram/slide-{i:02d}.jpg" for i in range(1, 8)],
            "instagram_caption": "instagram/caption.txt",
            "reel_brief": "reel-brief.txt"
        }
        (episode_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    csv_path = social_root / "pinterest-upload.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        fieldnames = ["Title", "Media URL", "Pinterest board", "Description", "Link", "Publish date", "Keywords"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"Generated social assets for {len(episodes)} episode(s) in {social_root}")


if __name__ == "__main__":
    main()
