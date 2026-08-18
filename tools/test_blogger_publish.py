#!/usr/bin/env python3
"""Blogger email 發佈工具的單元測試。"""

from __future__ import annotations

import json
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from blogger_email_publish import check_auth, post_content, publish


class FakeSmtp:
    instances = []

    def __init__(self, host, port, *, context):
        self.host = host
        self.port = port
        self.context = context
        self.login_args = None
        self.message = None
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def login(self, user, password):
        self.login_args = (user, password)

    def send_message(self, message):
        self.message = message


class BloggerPublishTests(unittest.TestCase):
    def test_post_content_escapes_metadata_and_story(self) -> None:
        metadata = {"description": "A <rare> creature"}
        content = post_content(metadata, "One & two.\n\n***\n\nThree.")
        self.assertIn("A &lt;rare&gt; creature", content)
        self.assertIn("One &amp; two.", content)
        self.assertIn("<hr>", content)
        self.assertIn("editorial-policy.html", content)
        self.assertTrue(content.endswith("#end"))
        self.assertNotIn("<p>#end</p>", content)

    def test_dry_run_skips_pending_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            package = source / "episodes" / "001-pending"
            package.mkdir(parents=True)
            (package / "approval.json").write_text(
                json.dumps({"status": "pending"}), encoding="utf-8"
            )
            self.assertEqual(publish(source, dry_run=True), 0)

    def test_check_auth_logs_in_without_sending(self) -> None:
        FakeSmtp.instances.clear()
        with patch.dict(
            os.environ,
            {
                "BLOGGER_SMTP_USER": "owner@example.com",
                "BLOGGER_SMTP_APP_PASSWORD": "abcd efgh ijkl mnop",
            },
            clear=True,
        ):
            check_auth(smtp_factory=FakeSmtp)
        smtp = FakeSmtp.instances[-1]
        self.assertEqual(smtp.login_args, ("owner@example.com", "abcdefghijklmnop"))
        self.assertIsNone(smtp.message)

    def test_publish_sends_approved_package_once(self) -> None:
        FakeSmtp.instances.clear()
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            package = source / "episodes" / "001-test-record"
            package.mkdir(parents=True)
            english = "The creature waits beside the old bell."
            (package / "english.txt").write_text(english, encoding="utf-8")
            (package / "metadata.json").write_text(
                json.dumps(
                    {
                        "slug": "test-record",
                        "episode": 1,
                        "title": "Test Record",
                        "description": "A test creature waits.",
                        "published_at": "2026-08-18",
                    }
                ),
                encoding="utf-8",
            )
            (package / "approval.json").write_text(
                json.dumps(
                    {
                        "status": "approved",
                        "decisions": [
                            {
                                "area": "creature_trait",
                                "decision": "The creature waits beside the old bell by choice.",
                            }
                        ],
                        "approved_english_sha256": hashlib.sha256(
                            english.encode("utf-8")
                        ).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )
            environment = {
                "BLOGGER_POST_EMAIL": "owner.secret@blogger.com",
                "BLOGGER_SMTP_USER": "owner@example.com",
                "BLOGGER_SMTP_APP_PASSWORD": "abcdefghijklmnop",
            }
            with patch.dict(os.environ, environment, clear=True):
                self.assertEqual(publish(source, smtp_factory=FakeSmtp), 1)
                self.assertEqual(publish(source, smtp_factory=FakeSmtp), 0)

            smtp = FakeSmtp.instances[-1]
            self.assertEqual(smtp.message["To"], "owner.secret@blogger.com")
            self.assertEqual(smtp.message["Subject"], "Field Record 001: Test Record")
            manifest = json.loads(
                (source / "operations" / "blogger-email-publications.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["test-record"]["status"], "sent")


if __name__ == "__main__":
    unittest.main()
