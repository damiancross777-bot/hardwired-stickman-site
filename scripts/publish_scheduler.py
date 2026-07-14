"""Fire episode go-live once the YouTube upload's own scheduled time has passed.

Reads content/publish_schedule.csv (episode_slug, scheduled_at, youtube_url), and for
each row whose target fire time (scheduled_at + 30min + a small deterministic random
jitter) has arrived: patches the episode JSON's youtube_url/youtube_id/thumbnail_url/
published_at, flips status "draft" -> "published", rebuilds the site, and pushes.

Designed to be run unattended on a recurring schedule (Windows Task Scheduler calls
this every N minutes) -- it's idempotent per-slug via state/publish_schedule_state.json,
so re-running it before or after a row's fire time is always safe.

CSV format (header row required):
    episode_slug,scheduled_at,youtube_url
    why-do-babies-smile,2026-07-20T18:00:00+10:00,https://www.youtube.com/watch?v=XXXXXXXXXXX

The 30-minute base delay exists so the site never links to a YouTube video before
YouTube's own scheduled release has actually gone live. The jitter is deterministic
per-slug (hashed from the slug), not re-rolled on every check, so the target time is
stable across repeated runs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "content" / "publish_schedule.csv"
STATE_DIR = ROOT / "state"
STATE_PATH = STATE_DIR / "publish_schedule_state.json"
LOG_PATH = STATE_DIR / "publish_schedule.log"
EPISODES_DIR = ROOT / "content" / "episodes"

JITTER_MIN_MINUTES = 0
JITTER_MAX_MINUTES = 15
BASE_DELAY_MINUTES = 30

YOUTUBE_ID_RE = re.compile(
    r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/|live/))([A-Za-z0-9_-]{11})"
)


def log(message: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now(timezone.utc).isoformat()}  {message}"
    print(line)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def deterministic_jitter_minutes(slug: str) -> float:
    digest = hashlib.sha256(slug.encode("utf-8")).hexdigest()
    span = JITTER_MAX_MINUTES - JITTER_MIN_MINUTES
    fraction = (int(digest[:8], 16) % 10_000) / 10_000
    return JITTER_MIN_MINUTES + fraction * span


def extract_video_id(url: str) -> str | None:
    match = YOUTUBE_ID_RE.search(url)
    return match.group(1) if match else None


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    full_cmd = cmd
    if cmd[0] == "git":
        full_cmd = ["git", "-c", f"safe.directory={ROOT.as_posix()}"] + cmd[1:]
    return subprocess.run(full_cmd, cwd=cwd, capture_output=True, text=True)


def apply_episode_update(slug: str, youtube_url: str, scheduled_at: str) -> bool:
    path = EPISODES_DIR / f"{slug}.json"
    if not path.exists():
        log(f"ERROR: no draft found for slug '{slug}' at {path}")
        return False

    video_id = extract_video_id(youtube_url)
    if not video_id:
        log(f"ERROR: could not extract a YouTube video ID from '{youtube_url}' for slug '{slug}'")
        return False

    episode = json.loads(path.read_text(encoding="utf-8"))
    episode["youtube_url"] = f"https://www.youtube.com/watch?v={video_id}"
    episode["youtube_id"] = video_id
    episode["thumbnail_url"] = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    episode["published_at"] = scheduled_at
    episode["updated_at"] = datetime.now(timezone.utc).isoformat()
    episode["status"] = "published"
    path.write_text(json.dumps(episode, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Updated {path.name}: video_id={video_id}, status=published")
    return True


def rebuild_and_push(python_exe: Path, changed_slugs: list[str]) -> bool:
    """Returns True only if the site was successfully rebuilt AND (nothing needed
    committing OR the commit+push both succeeded). Callers must not mark an
    episode as processed unless this returns True -- otherwise a transient
    failure here would silently and permanently strand that episode, since
    the JSON patch itself already happened and looks "done" locally."""
    for step in ("validate_content.py", "make_social.py", "build_site.py"):
        result = run([str(python_exe), f"scripts\\{step}"], cwd=ROOT)
        log(f"{step}: exit={result.returncode}")
        if result.stdout.strip():
            log(f"{step} stdout: {result.stdout.strip()[-800:]}")
        if result.returncode != 0:
            log(f"{step} stderr: {result.stderr.strip()[-800:]}")
            log("ABORTING push -- build step failed, site left unrebuilt/unpushed for manual review.")
            return False

    run(["git", "add", "-A"], cwd=ROOT)
    status = run(["git", "status", "--porcelain"], cwd=ROOT)
    if not status.stdout.strip():
        log("git: nothing to commit.")
        return True

    msg = "Publish scheduler: go-live for " + ", ".join(changed_slugs)
    commit = run(["git", "commit", "-m", msg], cwd=ROOT)
    log(f"git commit: exit={commit.returncode} {commit.stdout.strip()}")
    if commit.returncode != 0:
        log(f"git commit stderr: {commit.stderr.strip()[-800:]}")
        log("ABORTING -- commit failed, will retry on next check (episode not marked processed).")
        return False

    push = run(["git", "push"], cwd=ROOT)
    log(f"git push: exit={push.returncode} {push.stdout.strip()} {push.stderr.strip()}")
    if push.returncode != 0:
        log("ABORTING -- push failed, will retry on next check (episode not marked processed).")
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                         help="Compute/patch/state as normal but skip validate/social/build/git -- for safe testing.")
    args = parser.parse_args()

    if not CSV_PATH.exists():
        log(f"No {CSV_PATH.name} found -- nothing to do.")
        return

    state = load_state()
    now = datetime.now(timezone.utc)
    changed_slugs: list[str] = []

    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            slug = row.get("episode_slug", "").strip()
            scheduled_at_raw = row.get("scheduled_at", "").strip()
            youtube_url = row.get("youtube_url", "").strip()
            if not slug or not scheduled_at_raw or not youtube_url:
                continue

            entry = state.get(slug, {})
            if entry.get("processed"):
                continue

            try:
                scheduled_at = datetime.fromisoformat(scheduled_at_raw.replace("Z", "+00:00"))
            except ValueError:
                log(f"ERROR: unparseable scheduled_at '{scheduled_at_raw}' for slug '{slug}'")
                continue

            if "target_fire_time" not in entry:
                jitter = deterministic_jitter_minutes(slug)
                target = scheduled_at + timedelta(minutes=BASE_DELAY_MINUTES + jitter)
                entry["target_fire_time"] = target.isoformat()
                entry["scheduled_at"] = scheduled_at_raw
                entry["processed"] = False
                state[slug] = entry
                save_state(state)
                log(f"Scheduled '{slug}': fires at {target.isoformat()} "
                    f"({BASE_DELAY_MINUTES:.0f}min base + {jitter:.1f}min jitter after {scheduled_at_raw})")

            target = datetime.fromisoformat(entry["target_fire_time"])
            if now < target:
                continue

            if apply_episode_update(slug, youtube_url, scheduled_at_raw):
                changed_slugs.append(slug)

    if changed_slugs and args.dry_run:
        log(f"DRY RUN: would rebuild + push for: {', '.join(changed_slugs)} -- skipped.")
    elif changed_slugs:
        python_exe = ROOT / ".venv" / "Scripts" / "python.exe"
        if rebuild_and_push(python_exe, changed_slugs):
            for slug in changed_slugs:
                state[slug]["processed"] = True
                state[slug]["fired_at"] = now.isoformat()
            save_state(state)
        else:
            log(f"NOT marking {', '.join(changed_slugs)} as processed -- will retry next check "
                f"(JSON patch already applied and is idempotent, safe to reapply).")
    else:
        log("No episodes due -- no changes.")


if __name__ == "__main__":
    main()
