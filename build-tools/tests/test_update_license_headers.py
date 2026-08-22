#!/usr/bin/env python3
import unittest
from pathlib import Path
import tempfile
import os
import sys
import shutil

# Ensure parent directory (build-tools) is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from update_license_headers import (
    format_date_str,
    is_header_present,
    process_file
)

class TestUpdateLicenseHeaders(unittest.TestCase):

    def test_format_date_str_same_year(self):
        self.assertEqual(format_date_str(2026, 2026), "2026")

    def test_format_date_str_different_years(self):
        self.assertEqual(format_date_str(2021, 2026), "2021-2026")
        self.assertEqual(format_date_str(2014, 2026), "2014-2026")

    def test_is_header_present(self):
        with_header = "/*\n Copyright 2021 Jason Drake\n */\npackage org.javad;"
        without_header = "package org.javad;\n\npublic class Test {}"
        
        self.assertTrue(is_header_present(with_header))
        self.assertFalse(is_header_present(without_header))

    def test_process_file_existing_header_update(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            java_file = tmp_path / "Test.java"
            initial_content = "/*\n Copyright 2021 Jason Drake\n */\npackage org.javad;\n"
            java_file.write_text(initial_content, encoding="utf-8")

            template = "/*\n\tCopyright 2026 Jason Drake\n */\n"
            modified = process_file(java_file, template, 2026, tmp_path)

            self.assertTrue(modified)
            updated_content = java_file.read_text(encoding="utf-8")
            self.assertIn("Copyright 2021-2026", updated_content)

    def test_process_file_add_header(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            java_file = tmp_path / "Test.java"
            initial_content = "package org.javad;\n\npublic class Test {}"
            java_file.write_text(initial_content, encoding="utf-8")

            template = "/*\n\tCopyright 2026 Jason Drake\n */\n"
            modified = process_file(java_file, template, 2026, tmp_path)

            self.assertTrue(modified)
            updated_content = java_file.read_text(encoding="utf-8")
            self.assertTrue(updated_content.startswith("/*"))
            self.assertIn("Copyright 2026 Jason Drake", updated_content)

if __name__ == "__main__":
    unittest.main()
