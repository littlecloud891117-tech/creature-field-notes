#!/usr/bin/env python3
"""用 Blogger 的 email 發文功能發佈已核准的英文正篇。"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path
from typing import Callable

from envfile import load_env
from publish import paragraphs, validate

ROOT = Path(__file__).resolve().parent.parent
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f".env 缺少 {name}")
    return value


def post_content(metadata: dict, english: str) -> str:
    description = html.escape(str(metadata["description"]))
    body = paragraphs(english)
    return (
        f'<p class="field-note-intro"><em>{description}</em></p>'
        f'<article class="field-note-story">{body}</article>'
        '<hr><p><small>This episode passed a human creative review before publication. '
        '<a href="/p/editorial-policy.html">Read the editorial policy.</a></small></p>'
        "<p>#end</p>"
    )


def load_manifest(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Blogger 發佈紀錄格式錯誤：{path}")
    return value


def write_manifest(path: Path, manifest: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def approved_packages(source: Path) -> list[tuple[dict, str]]:
    approved: list[tuple[dict, str]] = []
    for package in sorted((source / "episodes").glob("*")):
        approval_path = package / "approval.json"
        if not package.is_dir() or not approval_path.exists():
            continue
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        if approval.get("status") != "approved":
            continue
        approved.append(validate(package))
    return approved


def smtp_login(
    user: str,
    app_password: str,
    *,
    smtp_factory: Callable = smtplib.SMTP_SSL,
):
    smtp = smtp_factory(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context())
    smtp.login(user, app_password.replace(" ", ""))
    return smtp


def check_auth(*, smtp_factory: Callable = smtplib.SMTP_SSL) -> None:
    load_env(ROOT / ".env")
    user = required("BLOGGER_SMTP_USER")
    password = required("BLOGGER_SMTP_APP_PASSWORD")
    with smtp_login(user, password, smtp_factory=smtp_factory):
        pass
    print("Gmail SMTP 驗證成功。")


def publish(
    source: Path,
    *,
    dry_run: bool = False,
    smtp_factory: Callable = smtplib.SMTP_SSL,
) -> int:
    load_env(ROOT / ".env")
    packages = approved_packages(source)
    manifest_path = source / "operations" / "blogger-email-publications.json"
    manifest = load_manifest(manifest_path)

    if dry_run:
        pending = 0
        for metadata, english in packages:
            slug = str(metadata["slug"])
            digest = hashlib.sha256(english.encode("utf-8")).hexdigest()
            previous = manifest.get(slug, {})
            if previous.get("status") != "sent" or previous.get("content_sha256") != digest:
                pending += 1
        print(f"Blogger dry-run 完成：{pending} 篇等待發佈")
        return pending

    post_email = required("BLOGGER_POST_EMAIL")
    user = required("BLOGGER_SMTP_USER")
    password = required("BLOGGER_SMTP_APP_PASSWORD")
    count = 0

    for metadata, english in packages:
        slug = str(metadata["slug"])
        digest = hashlib.sha256(english.encode("utf-8")).hexdigest()
        previous = manifest.get(slug)
        if previous and previous.get("status") == "sent":
            if previous.get("content_sha256") != digest:
                raise RuntimeError(f"已發佈內容有變更，請在 Blogger 手動更新：{slug}")
            continue
        if previous and previous.get("status") == "sending":
            raise RuntimeError(f"發佈狀態不明，請先在 Blogger 檢查是否有重複文章：{slug}")

        title = f"Field Record {int(metadata['episode']):03d}: {metadata['title']}"
        message_id = make_msgid(domain="creaturefieldnotes.blogspot.com")
        manifest[slug] = {
            "status": "sending",
            "title": title,
            "message_id": message_id,
            "content_sha256": digest,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        write_manifest(manifest_path, manifest)

        message = EmailMessage()
        message["From"] = user
        message["To"] = post_email
        message["Subject"] = title
        message["Message-ID"] = message_id
        message.set_content("This post requires an HTML-capable reader.\n\n#end")
        message.add_alternative(post_content(metadata, english), subtype="html")

        with smtp_login(user, password, smtp_factory=smtp_factory) as smtp:
            smtp.send_message(message)

        manifest[slug]["status"] = "sent"
        manifest[slug]["sent_at"] = datetime.now(timezone.utc).isoformat()
        write_manifest(manifest_path, manifest)
        count += 1

    print(f"Blogger email 發佈完成：{count} 篇")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check-auth", action="store_true")
    args = parser.parse_args()
    if args.check_auth:
        check_auth()
        return
    if args.source is None:
        parser.error("--source is required unless --check-auth is used")
    publish(args.source.resolve(), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
