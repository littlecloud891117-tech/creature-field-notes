#!/usr/bin/env python3
"""檢查公開網站的必要檔案與站內連結。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = (
    "index.html",
    "episodes/index.html",
    "about.html",
    "publishing.html",
    "privacy.html",
    "404.html",
    "robots.txt",
    "sitemap.xml",
    "feed.xml",
    ".nojekyll",
)
PRIVATE_MARKERS = ("review-zh-TW", "creative-decisions", '"status": "pending"')


def target_path(page: Path, raw: str) -> Path | None:
    value = urlsplit(raw)
    if value.scheme or value.netloc or raw.startswith(("#", "mailto:")):
        return None
    target = (page.parent / value.path).resolve()
    if value.path.endswith("/") or target.is_dir():
        target /= "index.html"
    return target


def check() -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).exists():
            errors.append(f"缺少必要檔案：{relative}")

    for page in ROOT.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        for marker in PRIVATE_MARKERS:
            if marker in text:
                errors.append(f"公開頁面含私人標記：{page.relative_to(ROOT)} -> {marker}")
        for raw in re.findall(r'(?:href|src)=["\']([^"\']+)', text):
            target = target_path(page, raw)
            if target is not None and not target.exists():
                errors.append(f"失效站內連結：{page.relative_to(ROOT)} -> {raw}")

    publications = ROOT / "data" / "publications.json"
    try:
        records = json.loads(publications.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"發佈清單無效：{error}")
    else:
        if not isinstance(records, list):
            errors.append("發佈清單必須是 JSON array")
        elif len({record.get("slug") for record in records}) != len(records):
            errors.append("發佈清單含重複 slug")
    return errors


def main() -> int:
    errors = check()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    pages = len(list(ROOT.rglob("*.html")))
    print(f"網站檢查通過：{pages} 個 HTML 頁面")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
