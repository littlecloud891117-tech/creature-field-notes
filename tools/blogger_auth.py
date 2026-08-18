#!/usr/bin/env python3
"""取得 Blogger OAuth 授權，並驗證目標 Blog。"""

from __future__ import annotations

import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from envfile import load_env

ROOT = Path(__file__).resolve().parent.parent
SCOPES = ["https://www.googleapis.com/auth/blogger"]


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f".env 缺少 {name}")
    return value


def main() -> None:
    load_env(ROOT / ".env")
    client_path = Path(required("BLOGGER_CLIENT_SECRET_FILE"))
    token_path = Path(required("BLOGGER_TOKEN_FILE"))
    blog_id = required("BLOGGER_BLOG_ID")
    if not client_path.is_file():
        raise RuntimeError(f"OAuth client 檔案不存在：{client_path}")
    token_path.parent.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SCOPES)
    credentials = flow.run_local_server(
        host="127.0.0.1",
        port=0,
        open_browser=True,
        access_type="offline",
        prompt="consent",
        success_message="Blogger authorization is complete. You can close this window.",
    )
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    service = build("blogger", "v3", credentials=credentials, cache_discovery=False)
    blog = service.blogs().get(blogId=blog_id).execute()
    print(f"Blogger 授權完成：{blog['name']} -> {blog['url']}")
    print(f"Token 已存到：{token_path}")


if __name__ == "__main__":
    main()
