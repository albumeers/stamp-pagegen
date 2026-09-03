#!/usr/bin/env python3
import unittest
from pathlib import Path
import tempfile
import sys

# Ensure parent directory (build-tools) is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bump_version import (
    get_current_version,
    increment_patch_version,
    bump_version
)

class TestBumpVersion(unittest.TestCase):

    def test_get_current_version(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pom_file = Path(tmp_dir) / "pom.xml"
            pom_file.write_text("<project>\n\t<version>2.6.3</version>\n</project>", encoding="utf-8")
            self.assertEqual(get_current_version(pom_file), "2.6.3")

    def test_increment_patch_version(self):
        self.assertEqual(increment_patch_version("2.6.3"), "2.6.4")
        self.assertEqual(increment_patch_version("1.0.0"), "1.0.1")
        with self.assertRaises(ValueError):
            increment_patch_version("2.6")

    def test_bump_version(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pom_file = Path(tmp_dir) / "pom.xml"
            initial_content = "<project>\n\t<version>2.6.3</version>\n</project>"
            pom_file.write_text(initial_content, encoding="utf-8")

            success = bump_version(pom_file, "2.6.4")
            self.assertTrue(success)
            self.assertEqual(get_current_version(pom_file), "2.6.4")

if __name__ == "__main__":
    unittest.main()
