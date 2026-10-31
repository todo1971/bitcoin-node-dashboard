# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "installer" / "web_installer.py"
SPEC = importlib.util.spec_from_file_location("web_installer", MODULE_PATH)
web_installer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(web_installer)


class InstallerValidationTests(unittest.TestCase):
    def test_integer_range(self):
        self.assertEqual(web_installer.parse_integer("60", 30, 3600, "value"), 60)
        with self.assertRaises(ValueError):
            web_installer.parse_integer("5", 30, 3600, "value")

    def test_public_ip_and_hostname(self):
        self.assertEqual(
            web_installer.validate_public_address("217.160.16.224"),
            "217.160.16.224",
        )
        self.assertEqual(
            web_installer.validate_public_address("node.example.org"),
            "node.example.org",
        )

    def test_rejects_invalid_hostname(self):
        with self.assertRaises(ValueError):
            web_installer.validate_public_address("../../etc/passwd")


if __name__ == "__main__":
    unittest.main()
