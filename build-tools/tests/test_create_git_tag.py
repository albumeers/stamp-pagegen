#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import sys

# Ensure parent directory (build-tools) is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from create_git_tag import (
    get_current_version,
    has_uncommitted_changes,
    create_git_tag
)

class TestCreateGitTag(unittest.TestCase):

    def test_get_current_version(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pom_file = Path(tmp_dir) / "pom.xml"
            pom_file.write_text("<project>\n\t<version>2.6.4</version>\n</project>", encoding="utf-8")
            self.assertEqual(get_current_version(pom_file), "2.6.4")

    @patch("subprocess.run")
    def test_has_uncommitted_changes(self, mock_run):
        mock_proc_clean = MagicMock()
        mock_proc_clean.stdout = ""
        mock_run.return_value = mock_proc_clean
        self.assertFalse(has_uncommitted_changes(Path("/tmp")))

        mock_proc_dirty = MagicMock()
        mock_proc_dirty.stdout = " M build-tools/create_git_tag.py\n"
        mock_run.return_value = mock_proc_dirty
        self.assertTrue(has_uncommitted_changes(Path("/tmp")))

    @patch("subprocess.run")
    def test_create_git_tag_uncommitted_changes(self, mock_run):
        mock_proc_dirty = MagicMock()
        mock_proc_dirty.stdout = " M build-tools/create_git_tag.py\n"
        mock_run.return_value = mock_proc_dirty

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            success = create_git_tag(repo_root, "2.6.4", push=True)
            self.assertFalse(success)

    @patch("subprocess.run")
    def test_create_git_tag_success(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_run.return_value = mock_proc

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            success = create_git_tag(repo_root, "2.6.4", push=True)
            self.assertTrue(success)

            self.assertEqual(mock_run.call_count, 3)
            status_call = mock_run.call_args_list[0][0][0]
            tag_call = mock_run.call_args_list[1][0][0]
            push_call = mock_run.call_args_list[2][0][0]

            self.assertEqual(status_call, ["git", "status", "--porcelain"])
            self.assertEqual(tag_call, ["git", "tag", "-a", "v2.6.4", "-m", "Created tag v2.6.4"])
            self.assertEqual(push_call, ["git", "push", "origin", "--tags"])

    @patch("subprocess.run")
    def test_create_git_tag_no_push(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_run.return_value = mock_proc

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            success = create_git_tag(repo_root, "2.6.4", push=False)
            self.assertTrue(success)

            self.assertEqual(mock_run.call_count, 2)
            status_call = mock_run.call_args_list[0][0][0]
            tag_call = mock_run.call_args_list[1][0][0]
            self.assertEqual(status_call, ["git", "status", "--porcelain"])
            self.assertEqual(tag_call, ["git", "tag", "-a", "v2.6.4", "-m", "Created tag v2.6.4"])

if __name__ == "__main__":
    unittest.main()
