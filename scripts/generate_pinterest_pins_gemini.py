"""Generate Gemini-rendered Pinterest pins from a user-selected production still.

Reads ../episodes/<ep>/Pin/ for:
  - a prompt template (*.txt) -- the Gemini prompt written for this purpose,
    with a bracketed [INSERT YOUR TOP HOOK TEXT HERE, ...] placeholder
  - one or more reference images (*.png/*.jpg/*.jpeg) the user has picked and
    placed there manually

Pairs each reference image with a hook line from that episode's metadata.txt
THUMBNAIL HOOK OPTIONS section (up to 3), substitutes the hook into the prompt
template, and sends the reference image + prompt to Gemini 2.5 Flash Image --
same model/SDK call pattern as step_images.py in the production pipeline.

If only one reference image is present (the common case), it's reused for all
(up to 3) hook variants. If multiple images are present, they're paired with
hooks in filename order, up to 3 pairs.

Output overwrites offplatform/output/social/<slug>/pinterest/pin-0N.jpg -- the
exact same filenames make_social.py's PIL-drawn pins use, so nothing else in
the pipeline (CSV export, site linking, Pinterest posting) needs to change.
Run this AFTER make_social.py for a given episode, not before -- make_social.py
would otherwise overwrite these with the plain PIL versions again.

This calls the paid Gemini image API -- run it yourself when ready, it is
never invoked automatically by any other script in this pipeline.

Usage:
    python scripts/generate_pinterest_pins_gemini.py 001
    python scripts/generate_pinterest_pins_gemini.py 001-why-do-babies-smile
"""
from __future__ import annotations

import argparse
import re
import sys
from io import BytesIO
from pathlib import Path

OFFPLATFORM_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ROOT = OFFPLATFORM_ROOT.parent
EPISODES_DIR = PRODUCTION_ROOT / "episodes"
OUTPUT_SOCIAL_DIR = OFFPLATFORM_ROOT / "output" / "social"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_episode import find_episode_dir, parse_metadata_txt, get_section  # noqa: E402

ASPECT_RATIO = "2:3"
IMAGE_SIZE = "1K"
FINAL_WIDTH, FINAL_HEIGHT = 1000, 1500
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def load_env() -> None:
    from dotenv import load_dotenv
    load_dotenv(PRODUCTION_ROOT / ".env")


def all_hook_options(section_text: str) -> list[str]:
    hooks = []
    for line in section_text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^\d+\.\s+(.+?)\s{2,}\[\d+ words?\]\s*$", line)
        if m:
            hooks.append(m.group(1).strip())
            continue
        m2 = re.match(r"^\d+\.\s+(.+)$", line)
        if m2:
            hooks.append(re.sub(r"\s*\[\d+ words?\]\s*$", "", m2.group(1)).strip())
    return hooks


def apply_hook(template_text: str, hook: str) -> str:
    return re.sub(r"\[INSERT YOUR TOP HOOK TEXT HERE.*?\]", hook.upper(), template_text, flags=re.DOTALL)


def find_pin_inputs(pin_dir: Path) -> tuple[Path, list[Path]]:
    txts = sorted(pin_dir.glob("*.txt"))
    if not txts:
        raise SystemExit(f"No prompt .txt found in {pin_dir}")
    images = sorted(p for p in pin_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not images:
        raise SystemExit(f"No reference image(s) found in {pin_dir} -- place one there first.")
    return txts[0], images


def build_pairs(images: list[Path], hooks: list[str]) -> list[tuple[Path, str]]:
    hooks = hooks[:3]
    if not hooks:
        raise SystemExit("No THUMBNAIL HOOK OPTIONS found in metadata.txt -- run step_metadata.py first.")
    if len(images) == 1:
        return [(images[0], hook) for hook in hooks]
    return list(zip(images, hooks))[:3]


def generate_pin(g, model: str, image_path: Path, prompt_text: str) -> bytes:
    from google.genai import types
    image_bytes = image_path.read_bytes()
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    contents = [
        "Reference image (source still to adapt into a Pinterest pin):",
        types.Part.from_bytes(data=image_bytes, mime_type=mime),
        prompt_text,
    ]
    resp = g.models.generate_content(
        model=model, contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(aspect_ratio=ASPECT_RATIO, image_size=IMAGE_SIZE)))
    for cand in resp.candidates:
        for part in cand.content.parts:
            if getattr(part, "inline_data", None) is not None:
                return part.inline_data.data
    reason = "unknown"
    try:
        reason = resp.candidates[0].finish_reason
    except Exception:
        pass
    raise SystemExit(f"Gemini returned no image (finish_reason={reason})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("episode", help="Episode folder name or leading number, e.g. '001' or '001-why-do-babies-smile'")
    args = parser.parse_args()

    load_env()
    import os
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit(f"GEMINI_API_KEY not found -- expected in {PRODUCTION_ROOT / '.env'}")

    ep_dir = find_episode_dir(args.episode)
    slug_json = None
    import json
    episode_json_path = ep_dir / "episode.json"
    if episode_json_path.exists():
        slug_json = json.loads(episode_json_path.read_text(encoding="utf-8")).get("slug")
    slug = slug_json or re.sub(r"^\d+[-_]?", "", ep_dir.name).lower()

    pin_dir = ep_dir / "Pin"
    if not pin_dir.is_dir():
        raise SystemExit(f"No Pin/ folder found at {pin_dir} -- create it and add a reference image first.")

    prompt_path, images = find_pin_inputs(pin_dir)
    template_text = prompt_path.read_text(encoding="utf-8")

    metadata_sections = parse_metadata_txt(ep_dir / "metadata.txt")
    hooks = all_hook_options(get_section(metadata_sections, "THUMBNAIL HOOK OPTIONS"))

    pairs = build_pairs(images, hooks)
    print(f"Episode: {ep_dir.name}  ->  site slug: {slug}")
    print(f"Prompt template: {prompt_path.name}")
    print(f"Generating {len(pairs)} pin(s):")
    for i, (img, hook) in enumerate(pairs, start=1):
        print(f"  {i}. image={img.name}  hook={hook!r}")

    from google import genai
    from PIL import Image
    g = genai.Client(api_key=api_key)

    out_dir = OUTPUT_SOCIAL_DIR / slug / "pinterest"
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, (img, hook) in enumerate(pairs, start=1):
        print(f"\n--- Pin {i}/{len(pairs)}: {hook!r} (from {img.name}) ---")
        prompt_text = apply_hook(template_text, hook)
        data = generate_pin(g, "gemini-2.5-flash-image", img, prompt_text)
        pil_img = Image.open(BytesIO(data)).convert("RGB")
        pil_img = pil_img.resize((FINAL_WIDTH, FINAL_HEIGHT), Image.LANCZOS)
        out_path = out_dir / f"pin-{i:02d}.jpg"
        pil_img.save(out_path, quality=92, optimize=True)
        print(f"Saved: {out_path}")

    print(f"\nDone. {len(pairs)} pin(s) written to {out_dir}")
    print("These overwrite make_social.py's plain versions -- no other pipeline "
          "step needs to change (CSV/site/Pinterest posting all reference the same filenames).")


if __name__ == "__main__":
    main()
