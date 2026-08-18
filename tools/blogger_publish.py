#!/usr/bin/env python3
"""把通過人類創作關卡的英文正篇發布到 Blogger。"""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from envfile import load_env
from publish import paragraphs, validate

ROOT = Path(__file__).resolve().parent.parent
SCOPES = ["https://www.googleapis.com/auth/blogger"]


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f".env 缺少 {name}")
    return value


def credentials() -> Credentials:
    token_path = Path(required("BLOGGER_TOKEN_FILE"))
    if not token_path.is_file():
        raise RuntimeError(f"Blogger token 不存在：{token_path}")
    value = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if value.expired and value.refresh_token:
        value.refresh(Request())
        token_path.write_text(value.to_json(), encoding="utf-8")
    if not value.valid:
        raise RuntimeError("Blogger token 無效；請重新執行 tools/setup-blogger.sh")
    return value


def post_content(metadata: dict, english: str) -> str:
    description = html.escape(str(metadata["description"]))
    body = paragraphs(english)
    return (
        f'<p class="field-note-intro"><em>{description}</em></p>'
        f'<article class="field-note-story">{body}</article>'
        '<hr><p><small>This episode passed a human creative review before publication. '
        '<a href="/p/editorial-policy.html">Read the editorial policy.</a></small></p>'
    )


def load_manifest(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Blogger 發布清單格式錯誤：{path}")
    return value


def publish(source: Path, *, dry_run: bool = False) -> int:
    load_env(ROOT / ".env")
    blog_id = required("BLOGGER_BLOG_ID")
    manifest_path = source / "operations" / "blogger-publications.json"
    manifest = load_manifest(manifest_path)
    approved: list[tuple[Path, dict, str]] = []
    for package in sorted((source / "episodes").glob("*")):
        approval_path = package / "approval.json"
        if not package.is_dir() or not approval_path.exists():
            continue
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        if approval.get("status") != "approved":
            continue
        metadata, english = validate(package)
        approved.append((package, metadata, english))
    if dry_run:
        print(f"Blogger dry-run 通過：{len(approved)} 回可發布")
        return len(approved)
    service = build("blogger", "v3", credentials=credentials(), cache_discovery=False)
    blog = service.blogs().get(blogId=blog_id).execute()
    count = 0
    for _, metadata, english in approved:
        slug = str(metadata["slug"])
        body = {
            "kind": "blogger#post",
            "blog": {"id": blog_id},
            "title": f"Field Record {int(metadata['episode']):03d}: {metadata['title']}",
            "content": post_content(metadata, english),
            "labels": ["Creature Field Notes", f"Episode {int(metadata['episode']):03d}"],
        }
        previous = manifest.get(slug)
        if previous:
            result = service.posts().patch(
                blogId=blog_id,
                postId=previous["post_id"],
                body=body,
            ).execute()
        else:
            result = service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()
        manifest[slug] = {
            "post_id": result["id"],
            "url": result.get("url", ""),
            "updated": result.get("updated", ""),
        }
        count += 1
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Blogger 發布完成：{count} 回 -> {blog['url']}")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    publish(args.source.resolve(), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
