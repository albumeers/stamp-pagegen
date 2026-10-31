# Copyright 2026 Jason Drake (jadrake75@gmail.com) and John Lechtanski
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Unit Tests for Thread Page Splitter (split-pages.py).
Tests:
1. Threshold evaluation (<= N skipped, > N split).
2. Option A zero-padded part naming ({stem}-Part01.html, etc.).
3. Bottom pagination navigation (< Previous and Next >).
4. Preservation of footer with last modified date across all parts.
5. Title and header badge updates.
6. Dry-run mode and directory scanning.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# Ensure src/main/python is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../main/python")))

# Import split-pages module dynamically
split_pages_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../main/python/util/split-pages.py"))
spec = importlib.util.spec_from_file_location("split_pages", split_pages_path)
split_pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(split_pages)


class TestSplitPages(unittest.TestCase):
    """Test suite for split-pages.py functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_sample_html(self, post_count: int, with_mod_log: bool = False, custom_title: str = "Test Thread") -> str:
        posts_html = []
        for i in range(1, post_count + 1):
            posts_html.append(
                f'<li id="post{1000 + i}" class="wbbPost message">\n'
                f'    <article class="messageContent">\n'
                f'        <div class="messageText"><p>Post content {i}</p></div>\n'
                f'        <footer class="messageFooter">\n'
                f'            <woltlab-core-date-time date="2026-10-18T10:0{i%10}:00+00:00">{i}. Oktober 2026</woltlab-core-date-time>\n'
                f'        </footer>\n'
                f'    </article>\n'
                f'</li>'
            )

        mod_log = ""
        if with_mod_log:
            mod_log = (
                f'<li class="modificationLogEntry lastModificationLogEntry" data-log-id="999">\n'
                f'    <article class="message messageReduced">\n'
                f'        <div>Hat das Thema verschoben. <woltlab-core-date-time date="2026-10-19T12:00:00+00:00">19. Oktober 2026</woltlab-core-date-time></div>\n'
                f'    </article>\n'
                f'</li>'
            )

        return (
            f'<!DOCTYPE html>\n'
            f'<html>\n'
            f'<head>\n'
            f'    <title>{custom_title} - Forum</title>\n'
            f'</head>\n'
            f'<body>\n'
            f'    <header class="contentHeader">\n'
            f'        <h1 class="contentTitle">{custom_title}</h1>\n'
            f'    </header>\n'
            f'    <ul class="wbbThreadPostList messageList">\n'
            f'        ' + '\n'.join(posts_html) + '\n'
            f'        ' + mod_log + '\n'
            f'    </ul>\n'
            f'    <footer id="pageFooter" class="pageFooter">\n'
            f'        <div class="copyright">WoltLab Suite</div>\n'
            f'    </footer>\n'
            f'</body>\n'
            f'</html>'
        )

    def test_split_small_file_skipped(self):
        sample = self._create_sample_html(post_count=3)
        input_file = os.path.join(self.temp_dir, "small-thread.html")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(sample)

        res = split_pages.split_html_file(input_file, posts_per_page=5)
        self.assertEqual(res["status"], "skipped")
        self.assertEqual(res["posts"], 3)
        self.assertEqual(len(res["generated_files"]), 0)

    def test_split_multi_part_naming_option_a(self):
        # 5 posts split into 2 posts per page -> 3 parts: Part 1 (2), Part 2 (2), Part 3 (1)
        # Part 1 retains base name (.html), parts 2+ get -Part02.html, etc.
        sample = self._create_sample_html(post_count=5, custom_title="Plattenfehler III")
        input_file = os.path.join(self.temp_dir, "Plattenfehler-III.html")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(sample)

        res = split_pages.split_html_file(input_file, posts_per_page=2)
        self.assertEqual(res["status"], "split")
        self.assertEqual(res["parts"], 3)
        self.assertEqual(len(res["generated_files"]), 3)

        expected_filenames = [
            "Plattenfehler-III.html",
            "Plattenfehler-III-Part02.html",
            "Plattenfehler-III-Part03.html",
        ]
        for expected in expected_filenames:
            part_path = os.path.join(self.temp_dir, expected)
            self.assertTrue(os.path.isfile(part_path), f"Expected {expected} to exist")

    def test_pagination_links_bottom_of_page(self):
        sample = self._create_sample_html(post_count=5, custom_title="Plattenfehler III")
        input_file = os.path.join(self.temp_dir, "Plattenfehler-III.html")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(sample)

        split_pages.split_html_file(input_file, posts_per_page=2)

        part1_path = os.path.join(self.temp_dir, "Plattenfehler-III.html")
        part2_path = os.path.join(self.temp_dir, "Plattenfehler-III-Part02.html")
        part3_path = os.path.join(self.temp_dir, "Plattenfehler-III-Part03.html")

        with open(part1_path, "r", encoding="utf-8") as f:
            p1 = f.read()
        with open(part2_path, "r", encoding="utf-8") as f:
            p2 = f.read()
        with open(part3_path, "r", encoding="utf-8") as f:
            p3 = f.read()

        # Part 1: Has 'Next >' linking to Part02, no '< Previous'
        self.assertIn('Next &gt;</a>', p1)
        self.assertIn('href="Plattenfehler-III-Part02.html"', p1)
        self.assertNotIn('&lt; Previous</a>', p1)
        self.assertIn("Part 1 of 3", p1)

        # Part 2: Has both '< Previous' linking to base file and 'Next >' linking to Part03
        self.assertIn('&lt; Previous</a>', p2)
        self.assertIn('href="Plattenfehler-III.html"', p2)
        self.assertIn('Next &gt;</a>', p2)
        self.assertIn('href="Plattenfehler-III-Part03.html"', p2)
        self.assertIn("Part 2 of 3", p2)

        # Part 3: Has '< Previous' linking to Part02, no 'Next >'
        self.assertIn('&lt; Previous</a>', p3)
        self.assertIn('href="Plattenfehler-III-Part02.html"', p3)
        self.assertNotIn('Next &gt;</a>', p3)
        self.assertIn("Part 3 of 3", p3)

    def test_footer_with_last_modified_date_preserved(self):
        # When source HTML has a lastModificationLogEntry, EVERY part must have it
        sample = self._create_sample_html(post_count=4, with_mod_log=True)
        input_file = os.path.join(self.temp_dir, "thread_with_mod.html")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(sample)

        split_pages.split_html_file(input_file, posts_per_page=2)

        p1_path = os.path.join(self.temp_dir, "thread_with_mod.html")
        p2_path = os.path.join(self.temp_dir, "thread_with_mod-Part02.html")

        for p_path in [p1_path, p2_path]:
            with open(p_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("modificationLogEntry lastModificationLogEntry", content)
            self.assertIn("Hat das Thema verschoben", content)
            self.assertIn("19. Oktober 2026", content)
            # Ensure document closing footer is intact
            self.assertIn('id="pageFooter"', content)

    def test_footer_with_synthesized_date_when_no_mod_log(self):
        # When source HTML lacks modificationLogEntry, a last modified footer note is synthesized
        sample = self._create_sample_html(post_count=4, with_mod_log=False)
        input_file = os.path.join(self.temp_dir, "thread_no_mod.html")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(sample)

        split_pages.split_html_file(input_file, posts_per_page=2)

        p1_path = os.path.join(self.temp_dir, "thread_no_mod.html")
        p2_path = os.path.join(self.temp_dir, "thread_no_mod-Part02.html")

        for p_path in [p1_path, p2_path]:
            with open(p_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("modificationLogEntry lastModificationLogEntry", content)
            self.assertIn("Letzte Änderung / Last Modified", content)

    def test_title_and_h1_badges(self):
        sample = self._create_sample_html(post_count=4, custom_title="Lübeck Postgeschichte")
        input_file = os.path.join(self.temp_dir, "Luebeck.html")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(sample)

        split_pages.split_html_file(input_file, posts_per_page=2)

        p2_path = os.path.join(self.temp_dir, "Luebeck-Part02.html")
        with open(p2_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("<title>Lübeck Postgeschichte (Part 2 of 2) - Forum</title>", content)
        self.assertIn('(Part 2 of 2)', content)

    def test_dry_run_mode(self):
        sample = self._create_sample_html(post_count=4)
        input_file = os.path.join(self.temp_dir, "dry_run_thread.html")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(sample)

        res = split_pages.split_html_file(input_file, posts_per_page=2, dry_run=True)
        self.assertEqual(res["status"], "split")
        self.assertEqual(res["parts"], 2)

        p2_path = os.path.join(self.temp_dir, "dry_run_thread-Part02.html")
        self.assertFalse(os.path.exists(p2_path), "File should not exist in dry-run mode")

    def test_split_directory(self):
        file1 = os.path.join(self.temp_dir, "thread1.html")
        file2 = os.path.join(self.temp_dir, "thread2.html")

        with open(file1, "w", encoding="utf-8") as f:
            f.write(self._create_sample_html(post_count=6))
        with open(file2, "w", encoding="utf-8") as f:
            f.write(self._create_sample_html(post_count=2))

        summary = split_pages.split_directory(self.temp_dir, posts_per_page=3)
        self.assertEqual(summary["scanned"], 2)
        self.assertEqual(summary["split"], 1)
        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(summary["total_parts_created"], 2)

    def test_cli_execution(self):
        sample = self._create_sample_html(post_count=4)
        input_file = os.path.join(self.temp_dir, "cli_thread.html")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(sample)

        cmd = [
            sys.executable,
            split_pages_path,
            input_file,
            "--posts", "2",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("SPLITTING", res.stdout)
        self.assertIn("cli_thread.html", res.stdout)
        self.assertIn("cli_thread-Part02.html", res.stdout)

        p2 = os.path.join(self.temp_dir, "cli_thread-Part02.html")
        self.assertTrue(os.path.isfile(p2))


if __name__ == "__main__":
    unittest.main()
