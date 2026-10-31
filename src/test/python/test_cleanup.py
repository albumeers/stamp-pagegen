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
Unit Tests for Philaforum HTML Cleanup Utility (cleanup.py) and Scraper Integration.
Tests:
1. Deduplication of `messageList > li.modificationLogEntry` elements.
2. Fixing blockquote display (block instead of grid in CSS and inline styles).
"""

import os
import shutil
import sys
import tempfile
import unittest

# Ensure src/main/python is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../main/python")))

from philaforum.cleanup import (
    clean_directory,
    clean_html_file,
    clean_modification_log_entries,
    find_modification_log_entries,
    fix_blockquote_display,
    strip_unwanted_scripts,
)
from philaforum.scraper import combine_thread_pages, prune_unwanted_html_elements


class TestCleanup(unittest.TestCase):
    """Test suite for cleanup.py and scraper integration."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_single_modification_log_retained(self):
        html = """
        <ul class="messageList">
            <li class="message">Post 1</li>
            <li class="modificationLogEntry lastModificationLogEntry" data-log-id="101">
                <article class="message messageReduced">Moved to Luebeck</article>
            </li>
        </ul>
        """
        cleaned, removed_count = clean_modification_log_entries(html)
        self.assertEqual(removed_count, 0)
        self.assertIn('data-log-id="101"', cleaned)
        self.assertIn("lastModificationLogEntry", cleaned)

    def test_multiple_modification_logs_keeps_single_lastModificationLogEntry(self):
        html = """
        <ul class="messageList">
            <li class="message">Post 1</li>
            <li class="modificationLogEntry" data-log-id="74326" data-is-summarized="0">
                <article class="message messageReduced">
                    <div>Moved to Altdeutschland</div>
                </article>
            </li>
            <li class="message">Post 2</li>
            <li class="modificationLogEntry lastModificationLogEntry" data-log-id="138059" data-is-summarized="0">
                <article class="message messageReduced">
                    <div>Moved to Luebeck</div>
                </article>
            </li>
        </ul>
        """
        cleaned, removed_count = clean_modification_log_entries(html)
        self.assertEqual(removed_count, 1)
        self.assertNotIn('data-log-id="74326"', cleaned)
        self.assertIn('data-log-id="138059"', cleaned)
        self.assertIn("lastModificationLogEntry", cleaned)
        self.assertIn("Post 1", cleaned)
        self.assertIn("Post 2", cleaned)

        # Confirm exactly one li.modificationLogEntry exists in cleaned output
        entries = find_modification_log_entries(cleaned)
        self.assertEqual(len(entries), 1)
        self.assertIn("lastModificationLogEntry", entries[0][2])

    def test_multiple_lastModificationLogEntry_keeps_latest_one(self):
        # Scenario occurring when combining multiple pages each having a lastModificationLogEntry
        html = """
        <ul class="messageList">
            <li class="message">Page 1 Post</li>
            <li class="modificationLogEntry lastModificationLogEntry" data-log-id="100">
                <article>Page 1 Log</article>
            </li>
            <li class="message">Page 2 Post</li>
            <li class="modificationLogEntry lastModificationLogEntry" data-log-id="200">
                <article>Page 2 Log</article>
            </li>
        </ul>
        """
        cleaned, removed_count = clean_modification_log_entries(html)
        self.assertEqual(removed_count, 1)
        self.assertNotIn('data-log-id="100"', cleaned)
        self.assertIn('data-log-id="200"', cleaned)
        self.assertIn("Page 1 Post", cleaned)
        self.assertIn("Page 2 Post", cleaned)

    def test_no_lastModificationLogEntry_keeps_last_and_adds_class(self):
        html = """
        <ul class="messageList">
            <li class="modificationLogEntry" data-log-id="1"><article>Log 1</article></li>
            <li class="modificationLogEntry" data-log-id="2"><article>Log 2</article></li>
        </ul>
        """
        cleaned, removed_count = clean_modification_log_entries(html)
        self.assertEqual(removed_count, 1)
        self.assertNotIn('data-log-id="1"', cleaned)
        self.assertIn('data-log-id="2"', cleaned)
        self.assertIn("lastModificationLogEntry", cleaned)

    def test_nested_li_tags_inside_modification_log(self):
        html = """
        <ul class="messageList">
            <li class="modificationLogEntry" data-log-id="nested1">
                <div class="container">
                    <ul>
                        <li>Nested Item 1</li>
                        <li>Nested Item 2</li>
                    </ul>
                </div>
            </li>
            <li class="modificationLogEntry lastModificationLogEntry" data-log-id="nested2">
                <div>Final note</div>
            </li>
        </ul>
        """
        cleaned, removed_count = clean_modification_log_entries(html)
        self.assertEqual(removed_count, 1)
        self.assertNotIn('data-log-id="nested1"', cleaned)
        self.assertNotIn("Nested Item 1", cleaned)
        self.assertIn('data-log-id="nested2"', cleaned)
        self.assertIn("Final note", cleaned)

    def test_clean_directory_and_dry_run(self):
        # File 1: Needs cleanup (2 entries)
        # File 2: Already clean (1 entry)
        # File 3: No modification entries
        file1 = os.path.join(self.temp_dir, "thread1.html")
        file2 = os.path.join(self.temp_dir, "thread2.html")
        file3 = os.path.join(self.temp_dir, "thread3.html")

        f1_content = """
        <ul class="messageList">
            <li class="modificationLogEntry" data-log-id="1"><article>Older</article></li>
            <li class="modificationLogEntry lastModificationLogEntry" data-log-id="2"><article>Newer</article></li>
        </ul>
        """
        f2_content = """
        <ul class="messageList">
            <li class="modificationLogEntry lastModificationLogEntry" data-log-id="99"><article>Only</article></li>
        </ul>
        """
        f3_content = """
        <ul class="messageList"><li class="message">Hello</li></ul>
        """

        with open(file1, "w", encoding="utf-8") as f:
            f.write(f1_content)
        with open(file2, "w", encoding="utf-8") as f:
            f.write(f2_content)
        with open(file3, "w", encoding="utf-8") as f:
            f.write(f3_content)

        # 1. Dry run: should report 1 file modified and 1 removed, but files on disk unchanged
        stats_dry = clean_directory(self.temp_dir, dry_run=True, recursive=True)
        self.assertEqual(stats_dry["scanned"], 3)
        self.assertEqual(stats_dry["modified"], 1)
        self.assertEqual(stats_dry["removed"], 1)

        with open(file1, "r", encoding="utf-8") as f:
            self.assertIn('data-log-id="1"', f.read())

        # 2. Active run: file1 modified on disk
        stats_active = clean_directory(self.temp_dir, dry_run=False, recursive=True)
        self.assertEqual(stats_active["scanned"], 3)
        self.assertEqual(stats_active["modified"], 1)
        self.assertEqual(stats_active["removed"], 1)

        with open(file1, "r", encoding="utf-8") as f:
            updated_f1 = f.read()
        self.assertNotIn('data-log-id="1"', updated_f1)
        self.assertIn('data-log-id="2"', updated_f1)

        # 3. Subsequent run: everything already clean
        stats_subsequent = clean_directory(self.temp_dir, dry_run=False, recursive=True)
        self.assertEqual(stats_subsequent["scanned"], 3)
        self.assertEqual(stats_subsequent["modified"], 0)
        self.assertEqual(stats_subsequent["removed"], 0)

    def test_combine_thread_pages_deduplicates_modification_logs(self):
        page1_html = """
        <html><body>
        <ul class="messageList">
            <li class="message">Post Page 1</li>
            <li class="modificationLogEntry" data-log-id="10"><article>Log Page 1</article></li>
        </ul>
        </body></html>
        """
        page2_html = """
        <html><body>
        <ul class="messageList">
            <li class="message">Post Page 2</li>
            <li class="modificationLogEntry lastModificationLogEntry" data-log-id="20"><article>Log Page 2</article></li>
        </ul>
        </body></html>
        """
        combined = combine_thread_pages(page1_html, [page2_html])
        entries = find_modification_log_entries(combined)
        self.assertEqual(len(entries), 1)
        self.assertIn('data-log-id="20"', combined)
        self.assertNotIn('data-log-id="10"', combined)

    def test_prune_unwanted_html_elements_deduplicates_modification_logs(self):
        sample_html = """
        <ul class="messageList">
            <li class="message">Original Post</li>
            <li class="modificationLogEntry" data-log-id="55">First move</li>
            <li class="modificationLogEntry lastModificationLogEntry" data-log-id="56">Second move</li>
        </ul>
        """
        pruned = prune_unwanted_html_elements(sample_html)
        entries = find_modification_log_entries(pruned)
        self.assertEqual(len(entries), 1)
        self.assertIn('data-log-id="56"', pruned)
        self.assertNotIn('data-log-id="55"', pruned)

    # -------------------------------------------------------------------------
    # Blockquote display tests: block instead of grid
    # -------------------------------------------------------------------------

    def test_fix_blockquote_display_in_scraper_print_stylesheet(self):
        html_input = """
        <html><head>
        <style id="scraper-print-stylesheet">
        @media screen, print {
            blockquote {
                margin: 12px 0 !important;
                padding: 10px 16px !important;
                border-left: 4px solid #0066cc !important;
                background-color: #f7f9fb !important;
                color: #333333 !important;
                font-style: italic !important;
            }
        }
        </style>
        </head><body>
        <blockquote class="quoteBox">A quote</blockquote>
        </body></html>
        """
        fixed, fixes = fix_blockquote_display(html_input)
        self.assertEqual(fixes, 1)
        self.assertIn("display: block !important;", fixed)
        self.assertIn("grid-template-columns: none !important;", fixed)
        self.assertIn("blockquote, .quoteBox", fixed)

    def test_fix_blockquote_display_with_existing_grid_in_css(self):
        html_input = """
        <html><head>
        <style id="scraper-print-stylesheet">
        blockquote, .quoteBox {
            display: grid;
            grid-template-columns: 24px 1fr;
        }
        </style>
        </head><body><blockquote class="quoteBox">Text</blockquote></body></html>
        """
        fixed, fixes = fix_blockquote_display(html_input)
        self.assertEqual(fixes, 1)
        self.assertIn("display: block !important", fixed)
        self.assertNotIn("display: grid", fixed)

    def test_fix_blockquote_display_inline_style(self):
        html_input = """
        <html><body>
        <blockquote class="quoteBox" style="display: grid; border: 1px solid black;">
            <div>Quoted content</div>
        </blockquote>
        </body></html>
        """
        fixed, fixes = fix_blockquote_display(html_input)
        self.assertGreaterEqual(fixes, 1)
        self.assertIn('style="display: block; border: 1px solid black;"', fixed)
        self.assertNotIn("display: grid", fixed)

    def test_fix_blockquote_display_injects_stylesheet_when_missing(self):
        html_input = """
        <html><head><title>No stylesheet</title></head><body>
        <blockquote class="quoteBox">Quoted content</blockquote>
        </body></html>
        """
        fixed, fixes = fix_blockquote_display(html_input)
        self.assertEqual(fixes, 1)
        self.assertIn('<style id="scraper-print-stylesheet">', fixed)
        self.assertIn("blockquote, .quoteBox", fixed)
        self.assertIn("display: block !important;", fixed)

    def test_fix_blockquote_display_idempotent(self):
        html_input = """
        <html><head>
        <style id="scraper-print-stylesheet">
        blockquote, .quoteBox {
            display: block !important;
            grid-template-columns: none !important;
            margin: 12px 0 !important;
        }
        </style>
        </head><body>
        <blockquote class="quoteBox">Quoted content</blockquote>
        </body></html>
        """
        fixed, fixes = fix_blockquote_display(html_input)
        self.assertEqual(fixes, 0)
        self.assertEqual(fixed, html_input)

    def test_clean_directory_with_blockquote_fixes(self):
        file1 = os.path.join(self.temp_dir, "thread_bq.html")
        f1_content = """
        <html><head>
        <style id="scraper-print-stylesheet">
        blockquote {
            margin: 10px;
        }
        </style>
        </head><body>
        <blockquote class="quoteBox">Test</blockquote>
        </body></html>
        """
        with open(file1, "w", encoding="utf-8") as f:
            f.write(f1_content)

        stats = clean_directory(self.temp_dir, dry_run=False, recursive=True)
        self.assertEqual(stats["scanned"], 1)
        self.assertEqual(stats["modified"], 1)
        self.assertEqual(stats["blockquotes_fixed"], 1)

        with open(file1, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("display: block !important;", content)

    def test_strip_unwanted_scripts_external_and_inline(self):
        html_input = """
        <html>
        <head>
            <title>Thread Title</title>
            <script src="https://philaforum.com/js/WoltLabSuite.Core.min.js?v=1732185324"></script>
            <script async src="https://www.googletagmanager.com/gtag/js?id=G-TH9F98VLFM"></script>
            <script type="application/ld+json">{"@context": "http://schema.org"}</script>
        </head>
        <body>
            <div class="content">Post Text</div>
            <script>
                var WCF_PATH = 'https://philaforum.com/';
                WCF.User.init(14545, 'stampineer');
            </script>
        </body>
        </html>
        """
        cleaned, removed = strip_unwanted_scripts(html_input)
        self.assertEqual(removed, 4)
        self.assertNotIn("WoltLabSuite.Core.min.js", cleaned)
        self.assertNotIn("googletagmanager.com", cleaned)
        self.assertNotIn("WCF_PATH", cleaned)
        self.assertNotIn("stampineer", cleaned)
        self.assertIn("Post Text", cleaned)
        self.assertNotIn("<script", cleaned.lower())

    def test_strip_unwanted_scripts_preserves_scraper_cleanup(self):
        html_input = """
        <html>
        <body>
            <script src="https://philaforum.com/js/WoltLabSuite.min.js"></script>
            <div class="content">Post Text</div>
            <script id="scraper-cleanup-wcf">
                (function() { cleanupWcfFooter(); })();
            </script>
        </body>
        </html>
        """
        # Default: preserve scraper scripts
        cleaned, removed = strip_unwanted_scripts(html_input, keep_scraper_scripts=True)
        self.assertEqual(removed, 1)
        self.assertNotIn("WoltLabSuite.min.js", cleaned)
        self.assertIn('id="scraper-cleanup-wcf"', cleaned)
        self.assertIn("cleanupWcfFooter()", cleaned)

        # Explicit: remove all scripts including scraper scripts
        cleaned_all, removed_all = strip_unwanted_scripts(html_input, keep_scraper_scripts=False)
        self.assertEqual(removed_all, 2)
        self.assertNotIn("<script", cleaned_all.lower())

    def test_strip_unwanted_scripts_preserves_noscript(self):
        html_input = """
        <html>
        <head>
            <script src="https://philaforum.com/js/test.js"></script>
            <noscript>
                <style>.jsOnly { display: none !important; }</style>
            </noscript>
        </head>
        <body>
            <p>Content</p>
        </body>
        </html>
        """
        cleaned, removed = strip_unwanted_scripts(html_input)
        self.assertEqual(removed, 1)
        self.assertNotIn("test.js", cleaned)
        self.assertIn("<noscript>", cleaned)
        self.assertIn(".jsOnly { display: none !important; }", cleaned)
        self.assertIn("</noscript>", cleaned)

    def test_strip_unwanted_scripts_empty_or_no_scripts(self):
        self.assertEqual(strip_unwanted_scripts(""), ("", 0))
        no_scripts = "<html><body><p>Hello world</p></body></html>"
        self.assertEqual(strip_unwanted_scripts(no_scripts), (no_scripts, 0))

    def test_clean_html_file_strips_scripts(self):
        file_path = os.path.join(self.temp_dir, "test_script.html")
        content = """
        <html>
        <head>
            <script src="https://philaforum.com/js/WoltLabSuite.Forum.min.js"></script>
        </head>
        <body>
            <p>Sample</p>
        </body>
        </html>
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        stats = clean_html_file(file_path, dry_run=False, strip_scripts=True)
        self.assertEqual(stats["scripts_removed"], 1)
        self.assertEqual(stats["total"], 1)

        with open(file_path, "r", encoding="utf-8") as f:
            cleaned_content = f.read()
        self.assertNotIn("<script", cleaned_content.lower())

    def test_clean_directory_with_scripts(self):
        file1 = os.path.join(self.temp_dir, "file_with_scripts.html")
        content = """
        <html>
        <head>
            <script src="https://philaforum.com/js/core.js"></script>
            <script>var x = 1;</script>
        </head>
        <body><p>Text</p></body>
        </html>
        """
        with open(file1, "w", encoding="utf-8") as f:
            f.write(content)

        # Test with strip_scripts=True (default)
        stats = clean_directory(self.temp_dir, dry_run=False, recursive=True, strip_scripts=True)
        self.assertEqual(stats["scanned"], 1)
        self.assertEqual(stats["modified"], 1)
        self.assertEqual(stats["scripts_removed"], 2)

        with open(file1, "r", encoding="utf-8") as f:
            cleaned = f.read()
        self.assertNotIn("<script", cleaned.lower())

    def test_clean_directory_no_strip_scripts(self):
        file1 = os.path.join(self.temp_dir, "file_keep_scripts.html")
        content = """
        <html>
        <head>
            <script src="https://philaforum.com/js/core.js"></script>
        </head>
        <body><p>Text</p></body>
        </html>
        """
        with open(file1, "w", encoding="utf-8") as f:
            f.write(content)

        stats = clean_directory(self.temp_dir, dry_run=False, recursive=True, strip_scripts=False)
        self.assertEqual(stats["scripts_removed"], 0)

        with open(file1, "r", encoding="utf-8") as f:
            unmodified = f.read()
        self.assertIn("core.js", unmodified)

    def test_scraper_prune_unwanted_html_elements_strips_scripts(self):
        raw_html = """
        <html>
        <head>
            <script src="https://philaforum.com/js/WoltLabSuite.Core.min.js?v=1732185324"></script>
        </head>
        <body>
            <ul class="messageList">
                <li class="message">Post content</li>
            </ul>
            <script>var WCF_PATH = 'https://philaforum.com/';</script>
        </body>
        </html>
        """
        pruned = prune_unwanted_html_elements(raw_html)
        self.assertNotIn("WoltLabSuite.Core.min.js", pruned)
        self.assertNotIn("WCF_PATH", pruned)
        self.assertNotIn("<script", pruned.lower())
        self.assertIn("Post content", pruned)


if __name__ == "__main__":
    unittest.main()
