from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paperless_cli.client import encode_multipart
from paperless_cli.client import parse_data_arg
from paperless_cli.client import parse_key_value
from paperless_cli.config import Profile
from paperless_cli.config import config_path
from paperless_cli.config import load_config
from paperless_cli.config import upsert_profile


class CliHelpersTest(unittest.TestCase):
    def test_parse_key_value(self) -> None:
        self.assertEqual(parse_key_value(["a=1", "b=two"]), {"a": "1", "b": "two"})

    def test_parse_data_at_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text('{"ok": true}')
            self.assertEqual(parse_data_arg(f"@{path}"), {"ok": True})

    def test_encode_multipart(self) -> None:
        content_type, body = encode_multipart(
            fields={"title": "x", "tags": [1, 2]},
            files={"document": ("a.txt", b"hello", "text/plain")},
        )
        self.assertIn("multipart/form-data", content_type)
        self.assertIn(b'name="title"', body)
        self.assertIn(b'filename="a.txt"', body)


class ConfigTest(unittest.TestCase):
    def test_upsert_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("XDG_CONFIG_HOME")
            os.environ["XDG_CONFIG_HOME"] = tmp
            try:
                upsert_profile(
                    Profile(
                        name="default",
                        base_url="https://example.test/",
                        token="abc",
                    )
                )
                data = json.loads(config_path().read_text())
                self.assertEqual(data["active_profile"], "default")
                config = load_config()
                self.assertEqual(config.profiles["default"].base_url, "https://example.test")
            finally:
                if old is None:
                    os.environ.pop("XDG_CONFIG_HOME", None)
                else:
                    os.environ["XDG_CONFIG_HOME"] = old


if __name__ == "__main__":
    unittest.main()
