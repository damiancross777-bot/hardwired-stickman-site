from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

from common import (
    PUBLIC_DIR, SITE_DIR, OUTPUT_DIR, absolute_url, ensure_clean_dir,
    format_date, load_episodes, load_site, slugify_simple
)


def copy_static() -> None:
    shutil.copytree(SITE_DIR / "static", PUBLIC_DIR / "static", dirs_exist_ok=True)
    social_dir = OUTPUT_DIR / "social"
    if social_dir.exists():
        shutil.copytree(social_dir, PUBLIC_DIR / "social", dirs_exist_ok=True)


def render_to(env: Environment, template: str, destination: Path, **context) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(env.get_template(template).render(**context), encoding="utf-8")


def build_sitemap(site: dict, episodes: list[dict]) -> None:
    paths = [
        ("", None),
        ("episodes/", None),
        ("human-behaviour/", None),
        ("animal-behaviour/", None),
        ("about/", None),
        ("privacy/", None),
    ]
    for episode in episodes:
        paths.append((f"episodes/{episode['slug']}/", episode.get("updated_at") or episode["published_at"]))

    entries = []
    for path, lastmod in paths:
        loc = absolute_url(site["site_url"], path)
        lastmod_xml = f"<lastmod>{lastmod[:10]}</lastmod>" if lastmod else ""
        entries.append(f"<url><loc>{xml_escape(loc)}</loc>{lastmod_xml}</url>")

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
    (PUBLIC_DIR / "sitemap.xml").write_text(xml, encoding="utf-8")


def build_rss(site: dict, episodes: list[dict]) -> None:
    items = []
    for episode in episodes[:30]:
        link = absolute_url(site["site_url"], f"episodes/{episode['slug']}/")
        published = datetime.fromisoformat(episode["published_at"]).strftime("%a, %d %b %Y %H:%M:%S %z")
        items.append(f"""
        <item>
          <title>{xml_escape(episode['title'])}</title>
          <link>{xml_escape(link)}</link>
          <guid>{xml_escape(link)}</guid>
          <pubDate>{published}</pubDate>
          <description>{xml_escape(episode['summary'])}</description>
        </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>{xml_escape(site['site_name'])}</title>
        <link>{xml_escape(site['site_url'])}</link>
        <description>{xml_escape(site['description'])}</description>
        <language>{xml_escape(site['language'])}</language>
        {''.join(items)}
      </channel>
    </rss>
    """
    (PUBLIC_DIR / "rss.xml").write_text(rss, encoding="utf-8")


def main() -> None:
    site = load_site()
    episodes = load_episodes()
    ensure_clean_dir(PUBLIC_DIR)
    copy_static()

    env = Environment(
        loader=FileSystemLoader(SITE_DIR / "templates"),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["date"] = format_date
    env.filters["slug"] = slugify_simple
    env.globals["absolute_url"] = absolute_url

    categories: dict[str, list[dict]] = {}
    for episode in episodes:
        episode["article_html"] = markdown.markdown(
            episode["article_markdown"],
            extensions=["extra", "sane_lists"]
        )
        episode["page_url"] = absolute_url(site["site_url"], f"episodes/{episode['slug']}/")
        episode["social_card_url"] = absolute_url(
            site["site_url"], f"social/{episode['slug']}/pinterest/pin-01.jpg"
        )
        categories.setdefault(episode["category"], []).append(episode)

    render_to(env, "index.html", PUBLIC_DIR / "index.html",
              site=site, episodes=episodes[:6], all_episodes=episodes)
    render_to(env, "list.html", PUBLIC_DIR / "episodes" / "index.html",
              site=site, title="All Episodes", intro="Every Hardwired Stickman explainer.", episodes=episodes)

    for category, category_episodes in categories.items():
        slug = slugify_simple(category)
        render_to(env, "list.html", PUBLIC_DIR / slug / "index.html",
                  site=site, title=category, intro=f"Research-backed explainers about {category.lower()}.",
                  episodes=category_episodes)

    # Ensure category landing pages exist even before content is added.
    for category in ["Human Behaviour", "Animal Behaviour"]:
        slug = slugify_simple(category)
        destination = PUBLIC_DIR / slug / "index.html"
        if not destination.exists():
            render_to(env, "list.html", destination,
                      site=site, title=category,
                      intro=f"Research-backed explainers about {category.lower()}.",
                      episodes=[])

    by_slug = {episode["slug"]: episode for episode in episodes}
    for episode in episodes:
        related = [by_slug[s] for s in episode.get("related_slugs", []) if s in by_slug]
        render_to(
            env, "episode.html",
            PUBLIC_DIR / "episodes" / episode["slug"] / "index.html",
            site=site, episode=episode, related=related
        )

    render_to(env, "about.html", PUBLIC_DIR / "about" / "index.html", site=site)
    render_to(env, "privacy.html", PUBLIC_DIR / "privacy" / "index.html", site=site)
    render_to(env, "404.html", PUBLIC_DIR / "404.html", site=site)

    search_index = [
        {
            "title": e["title"],
            "summary": e["summary"],
            "category": e["category"],
            "url": f"/episodes/{e['slug']}/"
        }
        for e in episodes
    ]
    (PUBLIC_DIR / "search-index.json").write_text(json.dumps(search_index, indent=2), encoding="utf-8")
    (PUBLIC_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {absolute_url(site['site_url'], 'sitemap.xml')}\n",
        encoding="utf-8"
    )

    build_sitemap(site, episodes)
    build_rss(site, episodes)

    print(f"Built {len(episodes)} episode(s) into {PUBLIC_DIR}")


if __name__ == "__main__":
    main()
