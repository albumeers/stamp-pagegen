#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import sys

# Ensure parent directory (build-tools) is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_release_notes import (
    format_tag_name,
    categorize_commit,
    generate_release_notes_md,
    get_git_commits
)

class TestGenerateReleaseNotes(unittest.TestCase):

    def test_format_tag_name(self):
        self.assertEqual(format_tag_name("2.6.3"), "v2.6.3")
        self.assertEqual(format_tag_name("v2.6.5"), "v2.6.5")
        self.assertEqual(format_tag_name("HEAD"), "HEAD")

    def test_categorize_commit(self):
        self.assertEqual(categorize_commit("Add new plate flaw layout option"), "Features")
        self.assertEqual(categorize_commit("Fix title and subtitle ordering bug"), "Fixes")
        self.assertEqual(categorize_commit("Clean up helper functions and imports"), "Refactoring & Maintenance")

    def test_generate_release_notes_md(self):
        commits = [
            "abc1234 Add support for multi-section consolidated PDFs",
            "def5678 Fix Open button enablement when PDF exists",
            "ghi9012 Refactor internal helper function names"
        ]
        md = generate_release_notes_md("v2.6.3", "v2.6.5", commits)

        self.assertIn("# Release Notes (v2.6.3 -> v2.6.5)", md)
        self.assertIn("## 🚀 Features", md)
        self.assertIn("- Add support for multi-section consolidated PDFs (`abc1234`)", md)
        self.assertIn("## 🐛 Fixes", md)
        self.assertIn("- Fix Open button enablement when PDF exists (`def5678`)", md)
        self.assertIn("## 🔧 Refactoring & Maintenance", md)
        self.assertIn("- Refactor internal helper function names (`ghi9012`)", md)

    @patch("subprocess.run")
    def test_get_git_commits(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "abc1234 Fix bug #47\ndef5678 Add new feature\n"
        mock_run.return_value = mock_proc

        commits = get_git_commits(Path("/tmp"), "v2.6.3", "v2.6.5")
        self.assertEqual(len(commits), 2)
        self.assertEqual(commits[0], "abc1234 Fix bug #47")
        self.assertEqual(commits[1], "def5678 Add new feature")

if __name__ == "__main__":
    unittest.main()
