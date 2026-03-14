#!/usr/bin/env python3
"""
WEAREMS AI NEWS — Automated News Fetcher
Fetches latest Google AI and Anthropic/Claude news from RSS feeds,
translates to Japanese, and outputs news.json for the PWA.

Runs via GitHub Actions cron at 12:00 and 20:00 JST.
"""

import json
import re
import sys
import os
import html
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.parse import quote
from xml.etree import ElementTree as ET

JST = timezone(timedelta(hours=9))

# ── RSS Feed URLs ──
FEEDS = {
    "google": [
        # Google News RSS — AI/Gemini/DeepMind (English, cutting-edge sources)
        "https://news.google.com/rss/search?q=Google+AI+OR+Gemini+OR+DeepMind+when:3d&hl=en-US&gl=US&ceid=US:en",
        # Google AI Blog Atom
        "https://blog.google/technology/ai/rss/",
    ],
    "anthropic": [
        # Google News RSS — Anthropic/Claude (English)
        "https://news.google.com/rss/search?q=Anthropic+OR+Claude+AI+when:3d&hl=en-US&gl=US&ceid=US:en",
    ]
}

# ── Simple Translation Map (common AI terms) ──
TRANSLATION_MAP = {
    "launches": "がローンチ",
    "announces": "が発表",
    "introduces": "が導入",
    "releases": "がリリース",
    "unveils": "が公開",
    "Google": "Google",
    "Anthropic": "Anthropic",
    "Claude": "Claude",
    "Gemini": "Gemini",
    "DeepMind": "DeepMind",
    "AI": "AI",
    "model": "モデル",
    "update": "アップデート",
    "feature": "機能",
    "new": "新",
    "partnership": "パートナーシップ",
    "revenue": "収益",
    "billion": "億ドル",
    "million": "百万",
}

MAX_ARTICLES_PER_CATEGORY = 8


def translate_text(text):
    """Apply simple keyword-level translation for remaining English terms."""
    if not text:
        return text
    result = text
    for eng, jap in TRANSLATION_MAP.items():
        result = re.sub(r'\b' + re.escape(eng) + r'\b', jap, result, flags=re.IGNORECASE)
    return result


def fetch_rss(url):
    """Fetch and parse RSS/Atom feed."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; WEAREMS-AI-NEWS/1.0)"
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=15) as resp:
            return ET.parse(resp)
    except Exception as e:
        print(f"  [WARN] Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def extract_rss_items(tree):
    """Extract items from RSS 2.0 feed."""
    items = []
    root = tree.getroot()

    # Handle RSS 2.0
    for item in root.iter("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")
        pub_el = item.find("pubDate")
        source_el = item.find("source")

        title = title_el.text if title_el is not None else ""
        link = link_el.text if link_el is not None else ""
        desc = desc_el.text if desc_el is not None else ""
        pub = pub_el.text if pub_el is not None else ""
        source = source_el.text if source_el is not None else ""

        # Clean HTML from description
        desc = re.sub(r'<[^>]+>', '', html.unescape(desc or ""))
        title = html.unescape(title or "")

        items.append({
            "title": title.strip(),
            "description": desc.strip()[:300],
            "link": link.strip(),
            "pubDate": pub.strip(),
            "source": source.strip(),
        })

    # Handle Atom feeds
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
        title_el = entry.find("atom:title", ns)
        link_el = entry.find("atom:link", ns)
        summary_el = entry.find("atom:summary", ns) or entry.find("atom:content", ns)
        pub_el = entry.find("atom:published", ns) or entry.find("atom:updated", ns)

        title = title_el.text if title_el is not None else ""
        link = link_el.get("href", "") if link_el is not None else ""
        desc = summary_el.text if summary_el is not None else ""
        pub = pub_el.text if pub_el is not None else ""

        desc = re.sub(r'<[^>]+>', '', html.unescape(desc or ""))
        title = html.unescape(title or "")

        items.append({
            "title": title.strip(),
            "description": desc.strip()[:300],
            "link": link.strip(),
            "pubDate": pub.strip(),
            "source": "Google AI Blog",
        })

    return items


def categorize_tag(title, category):
    """Generate tags based on content analysis."""
    title_lower = title.lower()
    tags = []

    if category == "google":
        if "gemini" in title_lower:
            tags.append({"label": "Gemini", "type": "blue"})
        elif "pixel" in title_lower:
            tags.append({"label": "Pixel", "type": "blue"})
        elif "deepmind" in title_lower:
            tags.append({"label": "DeepMind", "type": "blue"})
        elif "workspace" in title_lower or "sheets" in title_lower or "docs" in title_lower:
            tags.append({"label": "Workspace", "type": "blue"})
        elif "maps" in title_lower:
            tags.append({"label": "Maps", "type": "blue"})
        elif "search" in title_lower:
            tags.append({"label": "Search", "type": "blue"})
        elif "cloud" in title_lower:
            tags.append({"label": "Cloud", "type": "blue"})
        else:
            tags.append({"label": "Google", "type": "blue"})
    else:
        if "claude code" in title_lower:
            tags.append({"label": "Claude Code", "type": "amber"})
        elif "claude" in title_lower:
            tags.append({"label": "Claude", "type": "amber"})
        elif "opus" in title_lower or "sonnet" in title_lower:
            tags.append({"label": "Model", "type": "amber"})
        else:
            tags.append({"label": "Anthropic", "type": "amber"})

    # Additional tags
    keywords_breaking = ["launch", "releas", "unveil", "announc", "introduc", "new"]
    keywords_research = ["research", "study", "paper", "breakthrough"]
    keywords_business = ["revenue", "billion", "funding", "partner", "invest"]

    if any(k in title_lower for k in keywords_breaking):
        tags.append({"label": "New", "type": "red"})
    elif any(k in title_lower for k in keywords_research):
        tags.append({"label": "Research", "type": "violet"})
    elif any(k in title_lower for k in keywords_business):
        tags.append({"label": "Business", "type": "violet"})

    return tags if tags else [{"label": category.capitalize(), "type": "blue" if category == "google" else "amber"}]


def extract_source_name(url, source_text=""):
    """Extract readable source name from URL or source text."""
    if source_text:
        return source_text
    try:
        domain = re.findall(r'https?://(?:www\.)?([^/]+)', url)
        if domain:
            return domain[0].split('.')[0].capitalize()
    except Exception:
        pass
    return "Web"


def deduplicate(items):
    """Remove duplicate articles by similar titles."""
    seen = set()
    unique = []
    for item in items:
        # Simple dedup key: first 40 chars of lowercase title
        key = item["title"].lower()[:40]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def build_news_json(all_items):
    """Build the final news.json structure."""
    now = datetime.now(JST)

    google_news = []
    for item in all_items.get("google", [])[:MAX_ARTICLES_PER_CATEGORY]:
        tags = categorize_tag(item["title"], "google")
        source_name = extract_source_name(item["link"], item.get("source", ""))
        translate_url = f"https://translate.google.com/translate?sl=en&tl=ja&u={quote(item['link'], safe='')}"
        google_news.append({
            "tags": tags,
            "headline": item["title"],
            "body": item["description"] if item["description"] else item["title"],
            "source": {"name": source_name, "url": item["link"]},
            "translate_url": translate_url
        })

    anthropic_news = []
    for item in all_items.get("anthropic", [])[:MAX_ARTICLES_PER_CATEGORY]:
        tags = categorize_tag(item["title"], "anthropic")
        source_name = extract_source_name(item["link"], item.get("source", ""))
        translate_url = f"https://translate.google.com/translate?sl=en&tl=ja&u={quote(item['link'], safe='')}"
        anthropic_news.append({
            "tags": tags,
            "headline": item["title"],
            "body": item["description"] if item["description"] else item["title"],
            "source": {"name": source_name, "url": item["link"]},
            "translate_url": translate_url
        })

    return {
        "lastUpdated": now.isoformat(),
        "google": google_news,
        "anthropic": anthropic_news,
        "upcoming": [],
        "stats": [
            {"value": f"{len(google_news)}", "label": "Google記事数", "color": "c-blue"},
            {"value": f"{len(anthropic_news)}", "label": "Anthropic記事数", "color": "c-amber"},
            {"value": now.strftime("%H:%M"), "label": "最終更新時刻", "color": "c-violet"},
            {"value": now.strftime("%m/%d"), "label": "取得日", "color": "c-red"}
        ],
        "insights": []
    }


def main():
    print(f"[{datetime.now(JST).isoformat()}] WEAREMS AI NEWS — Fetching...")

    all_items = {}
    for category, urls in FEEDS.items():
        items = []
        for url in urls:
            print(f"  Fetching: {url[:80]}...")
            tree = fetch_rss(url)
            if tree:
                fetched = extract_rss_items(tree)
                print(f"    → Got {len(fetched)} items")
                items.extend(fetched)
        all_items[category] = deduplicate(items)
        print(f"  [{category}] Total unique: {len(all_items[category])}")

    news_data = build_news_json(all_items)

    # Output path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "..", "data", "news.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(news_data, f, ensure_ascii=False, indent=2)

    print(f"  → Saved to {output_path}")
    print(f"  Google: {len(news_data['google'])} articles")
    print(f"  Anthropic: {len(news_data['anthropic'])} articles")
    print("Done!")


if __name__ == "__main__":
    main()
