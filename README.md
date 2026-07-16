# Hardwired Stickman — Off-Platform Site

A free, scriptable off-platform publishing system for Hardwired Stickman.

**This is a separate tool from the video-production pipeline one level up** (`step0_ingest.py`, `step_voice.py`, etc.). It has its own Python venv, its own git repo, and deploys to its own destination (Cloudflare Pages) — it only *reads* finished production data, it never modifies it. See the project's `CLAUDE.md` §7-style reasoning: two pipelines, one channel identity.

It turns one episode JSON file into:

- A complete static episode page.
- Homepage and category updates.
- `Article`, `VideoObject`, `WebSite` and `Organization` structured data.
- `sitemap.xml`, `robots.txt`, RSS and a search index.
- Three Pinterest graphics at 1000 × 1500.
- A seven-slide Instagram carousel at 1080 × 1350.
- Instagram caption and hashtags.
- Pinterest bulk-upload CSV.
- A short-form Reel brief.
- A deployable `public/` directory for Cloudflare Pages.

## 1. Install

On Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup.ps1
```

The setup script creates `.venv`, installs Python dependencies and builds the sample episode.

Alternatively, from the production repo's own `menu.ps1`, the **W** and **V** options run the equivalent commands for you without needing to `cd` into this folder manually (see §4 below).

## 2. Preview locally

```powershell
.\publish.ps1 -NoGit -Preview
```

Open:

```text
http://localhost:8000
```

## 3. Update the brand and links

Edit:

```text
content/site.json
```

Replace the sample site URL and social URLs before launch. Brand colors here are already set to match `CLAUDE.md` §13.4's locked deep-charcoal/amber-gold palette — don't drift from those without updating both files together.

The site is live at the custom domain (added 16 Jul 2026):

```text
https://hardwiredstickman.com
```

Previously served from the Cloudflare Pages default subdomain
(`hardwired-stickman.pages.dev`), which still works as a fallback unless/
until removed as a custom domain in the Cloudflare Pages project settings.

## 4. Import an episode from the production pipeline (recommended)

Instead of hand-typing an episode JSON from scratch, pull in everything the video pipeline already produced and verified:

```powershell
.\.venv\Scripts\python.exe scripts\import_episode.py 001
```

(or from the production root's `menu.ps1`: select the episode with **F**, then choose **W**.)

This reads `../episodes/<episode>/{episode.json, metadata.txt, sources.json, script.md}` and writes a draft `content/episodes/<slug>.json` with the following **already filled in**:

- Title (from `metadata.txt`'s picked title option, or `episode.json` as a fallback)
- Category (mapped from `episode.json`'s `lane`)
- `summary` / `seo.description` (from `metadata.txt`'s entity-rich SEO line)
- `seo.keywords` and `instagram.hashtags` (from `metadata.txt`'s TAGS/HASHTAGS)
- `sources` (normalized from `sources.json` — handles both the 001-010 schema and the 011-020 schema; entries with no real URL are dropped rather than shipped as a broken link)
- `key_findings` — a naive shortlist pulled from Beat 4, **always needs a human trim/rewrite pass**

Everything the pipeline has no equivalent for is left as a `"TODO -- fill in before publish"` marker: `article_markdown` (a fresh long-form written article, **not** the spoken script verbatim), `pinterest.hooks`/`description`, `instagram.slides`/`caption`, `reel`, and the publish-time fields (`published_at`, `duration_iso`, `youtube_url`/`youtube_id` once the video is actually live). Fill those in by hand or with Claude's help, using `script.md` and `sources.json` as source material — then run:

```powershell
.\.venv\Scripts\python.exe scripts\validate_content.py
```

to confirm nothing's missing before building.

## 5. Create a new episode from scratch (manual, no production data)

```powershell
.\new-episode.ps1 -Title "Why Dogs Tilt Their Heads" -Category "Animal Behaviour"
```

This creates a blank draft JSON file in `content/episodes/`. Complete the content, replace all placeholders, set:

```json
"status": "published"
```

Then build:

```powershell
.\publish.ps1 -EpisodeFile ".\content\episodes\why-dogs-tilt-their-heads.json" -NoGit
```

## 6. Connect GitHub and Cloudflare Pages

1. Create a new GitHub repository (`hardwired-stickman-site` or similar) — **keep it separate from anything containing the production pipeline's `.env` or media files.**
2. In this folder:

```powershell
git init
git branch -M main
git add .
git commit -m "Initial Hardwired Stickman off-platform site"
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

3. In Cloudflare, create a Pages project from the GitHub repository.
4. Use these build settings:

```text
Build command:
pip install -r requirements.txt && python scripts/validate_content.py && python scripts/make_social.py && python scripts/build_site.py

Build output directory:
public
```

5. Deploy.

After that, this command rebuilds everything and pushes it:

```powershell
.\publish.ps1 -EpisodeFile ".\content\episodes\your-episode.json"
```

## 7. Pinterest workflow

The generated files appear under:

```text
output/social/<episode-slug>/pinterest/
```

The combined CSV appears at:

```text
output/social/pinterest-upload.csv
```

The CSV points to the public image URLs on your website. Deploy the site first so those URLs exist before importing the CSV.

Pinterest can change its accepted bulk-upload columns. The included CSV uses a practical publishing manifest, but compare its headers against Pinterest's current template before the first import.

## 8. Instagram workflow

The carousel appears under:

```text
output/social/<episode-slug>/instagram/
```

It includes:

```text
slide-01.jpg through slide-07.jpg
caption.txt
```

Upload or schedule these through Meta Business Suite until you add Instagram API publishing.

## 9. Publishing order

The recommended production order is:

```text
Research and script (production pipeline)
→ YouTube upload
→ import_episode.py (pulls production data in)
→ Complete the remaining TODO fields
→ Validate
→ Generate social assets
→ Build site
→ Git push
→ Cloudflare deployment
→ Pinterest bulk upload
→ Instagram scheduling
```

## 10. Important pre-launch replacements

Search the repository for:

```text
VIDEO_ID
example.com
replace-this
TODO -- fill in before publish
Add your public business email
```

Do not publish with those placeholders still present.

## 11. Automated go-live scheduling (13 Jul 2026)

An episode can be fully authored ahead of time (status `"draft"`, real `article_markdown`/Pinterest/Instagram content, `youtube_url` still `VIDEO_ID`) and then set to go live automatically once the YouTube upload's own scheduled release time arrives — no manual "flip the switch" step needed on the day.

**How it works:** add a row to `content/publish_schedule.csv`:

```csv
episode_slug,scheduled_at,youtube_url
why-dogs-tilt-their-heads,2026-07-27T18:00:00+10:00,https://www.youtube.com/watch?v=XXXXXXXXXXX
```

- `episode_slug` must match an existing `content/episodes/<slug>.json` (already authored via `import_episode.py`, just still in draft).
- `scheduled_at` is the exact time you scheduled the video to go public on YouTube.
- `youtube_url` is the real video URL — YouTube assigns this immediately on upload, even while the video is still scheduled/private, so you can add this row as soon as you've uploaded and scheduled the video, well before it airs.

A Windows Scheduled Task (`HardwiredStickman-PublishScheduler`, checks every 10 minutes) runs `scripts/publish_scheduler.py`, which waits until **30 minutes + a small randomized jitter (0-15 min) after `scheduled_at`** before doing anything — this guarantees the site never links to a video before YouTube's own scheduled release has actually gone live, and the jitter avoids every episode going live at an identical, obviously-automated offset. Once that time passes, it automatically:

1. Extracts the video ID from `youtube_url`
2. Patches `youtube_url` / `youtube_id` / `thumbnail_url` / `published_at` in the episode JSON
3. Flips `status` from `"draft"` to `"published"`
4. Rebuilds the site (`validate_content.py` → `make_social.py` → `build_site.py`)
5. Commits and pushes — Cloudflare Pages auto-deploys from there

Everything is logged to `state/publish_schedule.log` (gitignored, local only) and tracked per-slug in `state/publish_schedule_state.json` so re-running the check is always safe — a row is only ever fired once.

**Managing the task:**

```powershell
Get-ScheduledTask -TaskName "HardwiredStickman-PublishScheduler"      # check status
Start-ScheduledTask -TaskName "HardwiredStickman-PublishScheduler"    # trigger a check now
Disable-ScheduledTask -TaskName "HardwiredStickman-PublishScheduler"  # pause without deleting
Unregister-ScheduledTask -TaskName "HardwiredStickman-PublishScheduler" -Confirm:$false  # remove entirely
```

`scripts/publish_scheduler.py --dry-run` computes/patches everything except the rebuild+push step — useful for testing a new row without risking a bad push.

## 12. Folder map

```text
content/
  site.json
  episodes/
  publish_schedule.csv    <- go-live automation input, see Sec 11
scripts/
  import_episode.py       <- pulls from ../episodes/<ep>/ (production pipeline)
  publish_scheduler.py    <- go-live automation, run by Windows Task Scheduler
  validate_content.py
  make_social.py
  build_site.py
  new_episode.py
site/
  templates/
  static/
state/                    <- gitignored: publish_schedule_state.json, publish_schedule.log
output/
  social/
public/
publish.ps1
setup.ps1
new-episode.ps1
```

`output/`, `public/`, `state/` and `.venv/` are generated/local and intentionally excluded from Git. Cloudflare builds `public/` fresh on every deploy.

## 13. Optional next upgrades

- Add automatic Instagram Graph API publishing.
- Add Pinterest API publishing after production access is approved — Trial-access testing in progress as of 13 Jul 2026.
- Add an email newsletter.
- Add a client-side search interface using `search-index.json`.
- Add source-validation checks against DOI and publication metadata.
