#!/usr/bin/env python3
"""只把通過人類創作關卡的英文正篇發佈到公開網站。"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
BASE_URL = "https://littlecloud891117-tech.github.io/creature-field-notes"
ALLOWED_AREAS = {"character_motive", "relationship", "dialogue", "event_result", "creature_trait"}
LIST_START = "<!-- EPISODE_LIST_START -->"
LIST_END = "<!-- EPISODE_LIST_END -->"


class GateError(RuntimeError):
    """人類創作關卡紀錄不完整。"""


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GateError(f"JSON 根節點必須是 object：{path}")
    return value


def validate(package: Path) -> tuple[dict, str]:
    metadata = load_json(package / "metadata.json")
    approval = load_json(package / "approval.json")
    english = (package / "english.txt").read_text(encoding="utf-8").strip()
    if approval.get("status") != "approved":
        raise GateError(f"尚未核准：{package.name}")
    decisions = approval.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        raise GateError(f"缺少人類實質創意決定：{package.name}")
    for decision in decisions:
        if not isinstance(decision, dict) or decision.get("area") not in ALLOWED_AREAS:
            raise GateError(f"創意決定的 area 無效：{package.name}")
        if len(str(decision.get("decision", "")).strip()) < 20:
            raise GateError(f"創意決定內容過短：{package.name}")
    digest = hashlib.sha256(english.encode("utf-8")).hexdigest()
    if approval.get("approved_english_sha256") != digest:
        raise GateError(f"核准後英文正篇已變更：{package.name}")
    required = {"slug", "episode", "title", "description", "published_at"}
    if not required.issubset(metadata):
        raise GateError(f"metadata 欄位不完整：{package.name}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(metadata["slug"])):
        raise GateError(f"slug 格式錯誤：{package.name}")
    datetime.fromisoformat(str(metadata["published_at"]))
    return metadata, english


def paragraphs(text: str) -> str:
    blocks = []
    for block in re.split(r"\n\s*\n", text):
        safe = html.escape(block.strip()).replace("\n", "<br>\n")
        if safe == "***":
            blocks.append("<hr>")
        elif safe:
            blocks.append(f"<p>{safe}</p>")
    return "\n        ".join(blocks)


def page(metadata: dict, english: str) -> str:
    title = html.escape(str(metadata["title"]))
    description = html.escape(str(metadata["description"]), quote=True)
    episode = int(metadata["episode"])
    slug = metadata["slug"]
    date = html.escape(str(metadata["published_at"]))
    body = paragraphs(english)
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — Creature Field Notes</title>
  <meta name="description" content="{description}">
  <link rel="canonical" href="{BASE_URL}/episodes/{slug}/">
  <link rel="stylesheet" href="../../assets/styles.css">
</head>
<body>
  <header class="site-header"><nav class="shell nav" aria-label="Main navigation"><a class="brand" href="../../">Creature Field Notes</a><div class="nav-links"><a href="../">Episodes</a><a href="../../about.html">About</a><a href="../../publishing.html">Publishing</a></div></nav></header>
  <main class="shell page">
    <p class="eyebrow">Field record {episode:03d} / {date}</p><h1>{title}</h1>
    <p class="page-intro">{description}</p>
    <article class="story">{body}</article>
  </main>
  <footer class="site-footer"><div class="shell footer-grid"><span>© 2026 Creature Field Notes</span><div class="footer-links"><a href="../../privacy.html">Privacy</a><a href="../../publishing.html">Editorial policy</a></div></div></footer>
</body></html>
'''


def update_index(records: list[dict]) -> None:
    path = SITE / "episodes" / "index.html"
    text = path.read_text(encoding="utf-8")
    items = ["<ol class=\"episode-list\">"]
    for record in sorted(records, key=lambda item: int(item["episode"]), reverse=True):
        items.append(
            f'<li><span class="episode-meta">FIELD RECORD {int(record["episode"]):03d} / '
            f'{html.escape(record["published_at"])}</span><a href="{record["slug"]}/">'
            f'{html.escape(record["title"])}</a><p>{html.escape(record["description"])}</p></li>'
        )
    items.append("</ol>")
    replacement = "\n    ".join(items) if records else '<div class="empty"><h2>The first record is under review.</h2><p>No draft appears here before the review is complete.</p></div>'
    before, remainder = text.split(LIST_START, 1)
    _, after = remainder.split(LIST_END, 1)
    path.write_text(f"{before}{LIST_START}\n    {replacement}\n    {LIST_END}{after}", encoding="utf-8")


def update_discovery(records: list[dict]) -> None:
    base_pages = ("/", "/episodes/", "/about.html", "/publishing.html", "/privacy.html")
    urls = [f"  <url><loc>{BASE_URL}{suffix}</loc></url>" for suffix in base_pages]
    urls += [f"  <url><loc>{BASE_URL}/episodes/{item['slug']}/</loc></url>" for item in records]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"
    (SITE / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    updated = max((str(item["published_at"]) for item in records), default="2026-08-18") + "T00:00:00+08:00"
    entries = []
    for item in sorted(records, key=lambda value: int(value["episode"]), reverse=True):
        entries.append(f'''  <entry><title>{html.escape(item["title"])}</title><id>{BASE_URL}/episodes/{item["slug"]}/</id><link href="{BASE_URL}/episodes/{item["slug"]}/"/><updated>{item["published_at"]}T00:00:00+08:00</updated><summary>{html.escape(item["description"])}</summary></entry>''')
    feed = f'''<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Creature Field Notes</title><id>{BASE_URL}/</id>
  <link href="{BASE_URL}/feed.xml" rel="self"/><link href="{BASE_URL}/"/>
  <updated>{updated}</updated>
{chr(10).join(entries)}
</feed>
'''
    (SITE / "feed.xml").write_text(feed, encoding="utf-8")


def publish(source: Path) -> int:
    manifest_path = SITE / "data" / "publications.json"
    existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = {item["slug"]: item for item in existing}
    count = 0
    for package in sorted((source / "episodes").glob("*")):
        if not package.is_dir() or not (package / "approval.json").exists():
            continue
        approval = load_json(package / "approval.json")
        if approval.get("status") != "approved":
            continue
        metadata, english = validate(package)
        target = SITE / "episodes" / metadata["slug"]
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(page(metadata, english), encoding="utf-8")
        records[metadata["slug"]] = metadata
        count += 1
    ordered = sorted(records.values(), key=lambda item: int(item["episode"]))
    manifest_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_index(ordered)
    update_discovery(ordered)
    print(f"發佈輸出完成：{count} 回更新，公開清單共 {len(ordered)} 回")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    publish(args.source.resolve())


if __name__ == "__main__":
    main()
