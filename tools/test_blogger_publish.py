#!/usr/bin/env python3
"""Blogger 發布器的確定性測試。"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from blogger_publish import post_content, publish


class BloggerPublishTests(unittest.TestCase):
    def test_post_content_escapes_metadata_and_story(self) -> None:
        metadata = {"description": "A <rare> creature"}
        content = post_content(metadata, "One & two.\n\n***\n\nThree.")
        self.assertIn("A &lt;rare&gt; creature", content)
        self.assertIn("One &amp; two.", content)
        self.assertIn("<hr>", content)
        self.assertIn("editorial-policy.html", content)

    def test_dry_run_skips_pending_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            package = source / "episodes" / "001-pending"
            package.mkdir(parents=True)
            (package / "approval.json").write_text(
                json.dumps({"status": "pending"}), encoding="utf-8"
            )
            with patch.dict(os.environ, {"BLOGGER_BLOG_ID": "123"}, clear=False):
                self.assertEqual(publish(source, dry_run=True), 0)


if __name__ == "__main__":
    unittest.main()
