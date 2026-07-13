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

The current starter URL is:

```text
https://hardwired-stickman.pages.dev
```

Your Cloudflare Pages project name must be available for that exact address to work.

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

## 11. Folder map

```text
content/
  site.json
  episodes/
scripts/
  import_episode.py    <- pulls from ../episodes/<ep>/ (production pipeline)
  validate_content.py
  make_social.py
  build_site.py
  new_episode.py
site/
  templates/
  static/
output/
  social/
public/
publish.ps1
setup.ps1
new-episode.ps1
```

`output/`, `public/` and `.venv/` are generated/local and intentionally excluded from Git. Cloudflare builds `public/` fresh on every deploy.

## 12. Optional next upgrades

- Add automatic Instagram Graph API publishing.
- Add Pinterest API publishing after production access is approved.
- Add an email newsletter.
- Add a client-side search interface using `search-index.json`.
- Add source-validation checks against DOI and publication metadata.
- Task Scheduler automation — deliberately out of scope for this first iteration.
