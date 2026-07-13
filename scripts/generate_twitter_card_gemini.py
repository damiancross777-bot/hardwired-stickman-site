"""Generate one Gemini-rendered X (Twitter) card image from a user-selected still.

Reads ../episodes/<ep>/Twitter/ for:
  - a prompt template (*.txt) -- a lighter-touch treatment than the Pinterest
    pins: color/brand enhancement only, no baked-in hook text (the tweet's own
    caption already carries the hook, so text on the image would be redundant
    in a fast-scrolling text-heavy timeline)
  - one reference image (*.png/*.jpg/*.jpeg) the user has picked and placed
    there manually

Unlike Pinterest (3 pins per episode), X wants exactly one clean card. Sends
the reference image + prompt to Gemini 2.5 Flash Image -- same model/SDK call
pattern as step_images.py in the production pipeline and this folder's own
generate_pinterest_pins_gemini.py.

Output: offplatform/output/social/<slug>/twitter/card.jpg (1200x675, the
standard X/Twitter summary-card size).

This calls the paid Gemini image API -- run it yourself when ready, it is
never invoked automatically by any other script in this pipeline.

Usage:
    python scripts/generate_twitter_card_gemini.py 001
    python scripts/generate_twitter_card_gemini.py 001-why-do-babies-smile
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from io import BytesIO
from pathlib import Path

OFFPLATFORM_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ROOT = OFFPLATFORM_ROOT.parent
EPISODES_DIR = PRODUCTION_ROOT / "episodes"
OUTPUT_SOCIAL_DIR = OFFPLATFORM_ROOT / "output" / "social"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_episode import find_episode_dir  # noqa: E402

ASPECT_RATIO = "16:9"
IMAGE_SIZE = "1K"
FINAL_WIDTH, FINAL_HEIGHT = 1200, 675
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def load_env() -> None:
    from dotenv import load_dotenv
    load_dotenv(PRODUCTION_ROOT / ".env")


def find_card_inputs(twitter_dir: Path) -> tuple[Path, Path]:
    txts = sorted(twitter_dir.glob("*.txt"))
    if not txts:
        raise SystemExit(f"No prompt .txt found in {twitter_dir}")
    images = sorted(p for p in twitter_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not images:
        raise SystemExit(f"No reference image found in {twitter_dir} -- place one there first.")
    return txts[0], images[0]


def generate_card(g, model: str, image_path: Path, prompt_text: str) -> bytes:
    from google.genai import types
    image_bytes = image_path.read_bytes()
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    contents = [
        "Reference image (source still to adapt into an X/Twitter card):",
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
    episode_json_path = ep_dir / "episode.json"
    if episode_json_path.exists():
        slug_json = json.loads(episode_json_path.read_text(encoding="utf-8")).get("slug")
    slug = slug_json or re.sub(r"^\d+[-_]?", "", ep_dir.name).lower()

    twitter_dir = ep_dir / "Twitter"
    if not twitter_dir.is_dir():
        raise SystemExit(f"No Twitter/ folder found at {twitter_dir} -- create it and add a reference image + prompt first.")

    prompt_path, image_path = find_card_inputs(twitter_dir)
    prompt_text = prompt_path.read_text(encoding="utf-8")

    print(f"Episode: {ep_dir.name}  ->  site slug: {slug}")
    print(f"Prompt template: {prompt_path.name}")
    print(f"Reference image: {image_path.name}")

    from google import genai
    from PIL import Image
    g = genai.Client(api_key=api_key)

    out_dir = OUTPUT_SOCIAL_DIR / slug / "twitter"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n--- Generating card ---")
    data = generate_card(g, "gemini-2.5-flash-image", image_path, prompt_text)
    pil_img = Image.open(BytesIO(data)).convert("RGB")
    pil_img = pil_img.resize((FINAL_WIDTH, FINAL_HEIGHT), Image.LANCZOS)
    out_path = out_dir / "card.jpg"
    pil_img.save(out_path, quality=92, optimize=True)

    print(f"\nSaved: {out_path}")
    print("Post this manually on X, paired with the copy in content/episodes/<slug>.json's 'twitter' block.")


if __name__ == "__main__":
    main()
