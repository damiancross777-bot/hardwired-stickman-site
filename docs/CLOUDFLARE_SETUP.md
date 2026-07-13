# Cloudflare Pages setup

Use GitHub integration for the simplest deployment.

## Build settings

```text
Framework preset: None
Build command:
pip install -r requirements.txt && python scripts/validate_content.py && python scripts/make_social.py && python scripts/build_site.py

Build output directory:
public
```

## Environment

Python 3.11 or newer is recommended.

## Custom domain

A custom domain can be added later. Update `content/site.json` after the domain is connected, then rebuild so canonical URLs, structured data, RSS and the sitemap use the final domain.
