#!/usr/bin/env python3

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
Unit tests for philaforum_scraper.py
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

# Ensure src/main/python is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../main/python")))

from scraper.philaforum_scraper import (
    DEFAULT_BOARD_URL,
    NetworkRateLimiter,
    embed_and_link_images,
    extract_pagination_count,
    extract_threads_from_board,
    fetch_and_save_image,
    find_browser_executable,
    get_image_filename,
    is_decorative_image,
    neutralize_image_anchors,
    parse_arguments,
    render_html_to_pdf,
    sanitize_filename,
    sanitize_thread_html,
    scrape_board,
    scrape_thread,
)


class TestPhilaforumScraper(unittest.TestCase):

    def test_find_browser_executable_with_custom_valid_path(self):
        with tempfile.NamedTemporaryFile(suffix=".exe") as tmp:
            found = find_browser_executable(tmp.name)
            self.assertEqual(os.path.abspath(tmp.name), found)

    def test_find_browser_executable_auto_detection_or_error(self):
        try:
            browser = find_browser_executable()
            self.assertTrue(os.path.isfile(browser))
        except FileNotFoundError:
            # On systems without Chrome/Edge, this is valid
            pass

    def test_extract_pagination_count(self):
        # Case 1: Board pagination with 84 pages
        sample_board = (
            '<div class="contentInteractionPagination paginationTop">'
            '<woltlab-core-pagination page="1" count="84" '
            'url="https://philaforum.com/forum/board/54/?pageNo=%d"></woltlab-core-pagination>'
            '</div>'
        )
        self.assertEqual(extract_pagination_count(sample_board), 84)

        # Case 2: Thread pagination with 136 pages
        sample_thread = (
            '<woltlab-core-pagination page="1" count="136" '
            'url="https://philaforum.com/forum/thread/9857/?pageNo=%d">'
        )
        self.assertEqual(extract_pagination_count(sample_thread), 136)

        # Case 3: No pagination
        sample_none = "<div><p>Simple post without pagination</p></div>"
        self.assertEqual(extract_pagination_count(sample_none), 1)

    def test_extract_threads_from_board(self):
        sample_html = """
        <ol class="messageGroupList">
            <li class="messageGroup">
                <a href="https://philaforum.com/forum/thread/9857-kleinschriftstempel/?action=firstNew" class="messageGroupLink">
                    Kleinschriftstempel &amp; Abstempelungen
                </a>
            </li>
            <li class="messageGroup">
                <a href="/forum/thread/43312-plattenfehler-und-andere-besonderheiten/" class="messageGroupLink">
                    Plattenfehler &quot;Germania&quot;
                </a>
            </li>
            <li class="messageGroup">
                <!-- Duplicate thread link with different query parameter -->
                <a href="https://philaforum.com/forum/thread/9857-kleinschriftstempel/" class="messageGroupLink">
                    Kleinschriftstempel
                </a>
            </li>
        </ol>
        """
        threads = extract_threads_from_board(sample_html)
        self.assertEqual(len(threads), 2)  # Deduplicated

        # Verify thread 1
        self.assertEqual(threads[0][0], "https://philaforum.com/forum/thread/9857-kleinschriftstempel/")
        self.assertEqual(threads[0][1], "Kleinschriftstempel & Abstempelungen")

        # Verify thread 2 (normalized domain)
        self.assertEqual(
            threads[1][0],
            "https://philaforum.com/forum/thread/43312-plattenfehler-und-andere-besonderheiten/",
        )
        self.assertEqual(threads[1][1], 'Plattenfehler "Germania"')

    def test_sanitize_thread_html(self):
        sample_html = (
            "<!DOCTYPE html><html><head><title>Test Thread</title></head><body>"
            '<div id="pageHeaderContainer">Header Nav</div>'
            '<article class="message"><div class="messageBody">'
            '<img src="https://philaforum.com/attachment/30996-sample-jpg/?thumbnail=1">'
            "</div></article>"
            '<div id="pageFooter">Footer</div></body></html>'
        )

        sanitized = sanitize_thread_html(sample_html, base_url="https://philaforum.com/")

        # Verify <base href="..."> is stripped so local relative links (e.g. ../images/) resolve locally
        self.assertNotIn("<base href", sanitized)

        # Verify thumbnail upgrade and inline base64 image embedding
        self.assertNotIn("?thumbnail=1", sanitized)
        self.assertTrue("data:image/" in sanitized or "https://philaforum.com/attachment/30996-sample-jpg" in sanitized)

        # Verify print CSS is injected
        self.assertIn("@media print", sanitized)
        self.assertIn("#pageHeaderContainer", sanitized)
        self.assertIn("display: none !important;", sanitized)

        # Verify layout min-width override and word wrapping rules
        self.assertIn("--wcfLayoutMinWidth: 0px !important;", sanitized)
        self.assertIn("word-break: break-word !important;", sanitized)
        self.assertIn(".layoutBoundary", sanitized)

        # Verify page-break fluidity rules
        self.assertIn("break-after: avoid !important;", sanitized)
        self.assertIn("break-inside: auto !important;", sanitized)

        # Verify user details de-emphasis & avatar removal
        self.assertIn(".userAvatar", sanitized)
        self.assertIn("transform: scale(0.65) !important;", sanitized)
        self.assertIn("flex-basis: calc(100% - 160px) !important;", sanitized)
        self.assertIn("max-width: calc(100% - 160px) !important;", sanitized)

    def test_sanitize_filename(self):
        raw = "Deutsches Reich: 1872/1945 *Rare* <Germania>?"
        clean = sanitize_filename(raw)
        self.assertNotIn(":", clean)
        self.assertNotIn("/", clean)
        self.assertNotIn("*", clean)
        self.assertNotIn("<", clean)
        self.assertNotIn(">", clean)
        self.assertNotIn("?", clean)
        self.assertEqual(clean, "Deutsches_Reich_18721945_Rare_Germania")

    def test_sanitize_title_slug(self):
        from scraper.philaforum_scraper import sanitize_title_slug
        # Text title with spaces to hyphens, caps preserved
        self.assertEqual(sanitize_title_slug("Dienstbrief aus 1941"), "Dienstbrief-aus-1941")
        # Leading thread ID stripped and capitalized
        self.assertEqual(sanitize_title_slug("1174-dienstbrief-aus-1941"), "Dienstbrief-aus-1941")
        # Special characters removed and spaces replaced
        self.assertEqual(sanitize_title_slug('Briefmarken: "Germania" / 1923?'), "Briefmarken-Germania-1923")

    def test_parse_arguments(self):
        # Test defaults
        args = parse_arguments([])
        self.assertIsNone(args.board_url)
        self.assertIsNone(args.board)
        self.assertFalse(args.first_page_only)
        self.assertIsNone(args.thread_url)
        self.assertIsNone(args.max_threads)
        self.assertIsNone(args.max_pages)
        self.assertIsNone(args.lang)

        # Test --board flag
        args_board = parse_arguments(["--board", "Deutsches-Reich-1872-1945"])
        self.assertEqual(args_board.board, "Deutsches-Reich-1872-1945")

        # Test --lang flag
        args_lang = parse_arguments(["--lang", "en"])
        self.assertEqual(args_lang.lang, "en")

        # Test --first-page-only flag
        args_first = parse_arguments(["--first-page-only", "--max-threads", "5"])
        self.assertTrue(args_first.first_page_only)
        self.assertEqual(args_first.max_threads, 5)

        # Test single thread URL
        args_thread = parse_arguments(["--thread-url", "https://philaforum.com/forum/thread/9857/"])
        self.assertEqual(args_thread.thread_url, "https://philaforum.com/forum/thread/9857/")

    @patch("scraper.philaforum_scraper.fetch_url")
    @patch("scraper.philaforum_scraper.render_html_to_pdf")
    def test_scrape_thread_first_page_only(self, mock_render, mock_fetch):
        mock_fetch.return_value = (
            '<html><head></head><body><woltlab-core-pagination count="5"></woltlab-core-pagination></body></html>'
        )
        mock_render.return_value = True

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("os.path.getsize", return_value=1024):
                pdfs = scrape_thread(
                    thread_url="https://philaforum.com/forum/thread/123-sample/",
                    output_dir=tmp_dir,
                    browser_path="dummy_browser",
                    first_page_only=True,
                    delay=0,
                )

        # Exactly 1 page should be scraped even though total pages is 5
        self.assertEqual(len(pdfs), 1)
        self.assertEqual(mock_fetch.call_count, 1)
        self.assertTrue(pdfs[0].endswith("Sample.pdf"))

    @patch("scraper.philaforum_scraper.fetch_url")
    @patch("scraper.philaforum_scraper.render_html_to_pdf")
    def test_scrape_thread_max_pages_limit(self, mock_render, mock_fetch):
        mock_fetch.return_value = (
            '<html><head></head><body><woltlab-core-pagination count="10"></woltlab-core-pagination></body></html>'
        )
        mock_render.return_value = True

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("os.path.getsize", return_value=1024):
                pdfs = scrape_thread(
                    thread_url="https://philaforum.com/forum/thread/123-sample/",
                    output_dir=tmp_dir,
                    browser_path="dummy_browser",
                    first_page_only=False,
                    max_pages=2,
                    delay=0,
                )

        # Limited to 2 pages, combined into a single PDF
        self.assertEqual(len(pdfs), 1)
        self.assertEqual(mock_fetch.call_count, 2)
        self.assertEqual(mock_render.call_count, 1)
        self.assertTrue(pdfs[0].endswith("Sample.pdf"))

    @patch("scraper.philaforum_scraper.scrape_thread")
    @patch("scraper.philaforum_scraper.fetch_url")
    def test_scrape_board_first_page_only(self, mock_fetch, mock_scrape_thread):
        board_html = """
        <html>
        <woltlab-core-pagination count="20"></woltlab-core-pagination>
        <a href="https://philaforum.com/forum/thread/100-thread1/" class="messageGroupLink">T1</a>
        <a href="https://philaforum.com/forum/thread/200-thread2/" class="messageGroupLink">T2</a>
        </html>
        """
        mock_fetch.return_value = board_html
        mock_scrape_thread.return_value = ["dummy.pdf"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            pdfs = scrape_board(
                board_url="https://philaforum.com/forum/board/54/",
                output_dir=tmp_dir,
                browser_path="dummy_browser",
                first_page_only=True,
                delay=0,
            )

        # Only board page 1 should be crawled
        self.assertEqual(mock_fetch.call_count, 1)
        # Both threads from board page 1 processed
        self.assertEqual(mock_scrape_thread.call_count, 2)

    def test_parse_iso_datetime(self):
        from scraper.philaforum_scraper import parse_iso_datetime
        dt1 = parse_iso_datetime("2026-10-14T10:48:18+00:00")
        self.assertIsNotNone(dt1.tzinfo)
        self.assertEqual(dt1.year, 2026)

        dt2 = parse_iso_datetime("2026-10-14T10:48:18Z")
        self.assertIsNotNone(dt2.tzinfo)
        self.assertEqual(dt2.hour, 10)

        dt3 = parse_iso_datetime("2016-07-01")
        self.assertEqual(dt3.year, 2016)
        self.assertEqual(dt3.month, 7)
        self.assertEqual(dt3.day, 1)

    def test_load_and_save_last_updated(self):
        from scraper.philaforum_scraper import load_last_updated, save_last_updated, parse_iso_datetime
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Initially None
            self.assertIsNone(load_last_updated(tmp_dir))

            target_dt = parse_iso_datetime("2026-10-14T12:00:00+00:00")
            save_last_updated(tmp_dir, target_dt, "https://philaforum.com/thread/1", "Test Thread")

            loaded = load_last_updated(tmp_dir)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.timestamp(), target_dt.timestamp())

    def test_parse_arguments_new_options(self):
        args = parse_arguments(["--force", "--max-articles", "10", "--oldest-first"])
        self.assertTrue(args.force)
        self.assertEqual(args.max_articles, 10)
        self.assertTrue(args.oldest_first)

    @patch("scraper.philaforum_scraper.scrape_thread")
    @patch("scraper.philaforum_scraper.fetch_url")
    def test_scrape_board_incremental_filtering(self, mock_fetch, mock_scrape_thread):
        from scraper.philaforum_scraper import save_last_updated, parse_iso_datetime
        board_html = """
        <html>
        <woltlab-core-pagination count="1"></woltlab-core-pagination>
        <ol id="thread1" class="tabularListColumns messageGroup wbbThread">
            <a href="https://philaforum.com/forum/thread/1-new/" class="messageGroupLink">New Thread</a>
            <woltlab-core-date-time date="2026-10-14T12:00:00+00:00"></woltlab-core-date-time>
        </ol>
        <ol id="thread2" class="tabularListColumns messageGroup wbbThread">
            <a href="https://philaforum.com/forum/thread/2-old/" class="messageGroupLink">Old Thread</a>
            <woltlab-core-date-time date="2026-10-14T11:00:00+00:00"></woltlab-core-date-time>
        </ol>
        </html>
        """
        mock_fetch.return_value = board_html
        mock_scrape_thread.return_value = ["dummy.pdf"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Set recorded date to 11:50:00 (10 mins before New Thread, 50 mins after Old Thread)
            rec_dt = parse_iso_datetime("2026-10-14T11:50:00+00:00")
            save_last_updated(tmp_dir, rec_dt, "https://philaforum.com/thread/prev", "Prev")

            pdfs = scrape_board(
                board_url="https://philaforum.com/forum/board/54/",
                output_dir=tmp_dir,
                browser_path="dummy_browser",
                force=False,
                delay=0,
            )

            # Only thread 1 (12:00:00 >= 11:49:00 cutoff) should be processed, thread 2 stopped
            self.assertEqual(mock_scrape_thread.call_count, 1)

    @patch("scraper.philaforum_scraper.scrape_thread")
    @patch("scraper.philaforum_scraper.fetch_url")
    def test_scrape_board_force_bypasses_cutoff(self, mock_fetch, mock_scrape_thread):
        from scraper.philaforum_scraper import save_last_updated, parse_iso_datetime
        board_html = """
        <html>
        <woltlab-core-pagination count="1"></woltlab-core-pagination>
        <ol id="thread1" class="tabularListColumns messageGroup wbbThread">
            <a href="https://philaforum.com/forum/thread/1-new/" class="messageGroupLink">New Thread</a>
            <woltlab-core-date-time date="2026-10-14T12:00:00+00:00"></woltlab-core-date-time>
        </ol>
        <ol id="thread2" class="tabularListColumns messageGroup wbbThread">
            <a href="https://philaforum.com/forum/thread/2-old/" class="messageGroupLink">Old Thread</a>
            <woltlab-core-date-time date="2026-10-14T11:00:00+00:00"></woltlab-core-date-time>
        </ol>
        </html>
        """
        mock_fetch.return_value = board_html
        mock_scrape_thread.return_value = ["dummy.pdf"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Recorded date is future 12:30:00
            rec_dt = parse_iso_datetime("2026-10-14T12:30:00+00:00")
            save_last_updated(tmp_dir, rec_dt)

            # With force=True, cutoff is ignored
            pdfs = scrape_board(
                board_url="https://philaforum.com/forum/board/54/",
                output_dir=tmp_dir,
                browser_path="dummy_browser",
                force=True,
                delay=0,
            )

            self.assertEqual(mock_scrape_thread.call_count, 2)

    @patch("scraper.philaforum_scraper.scrape_thread")
    @patch("scraper.philaforum_scraper.fetch_url")
    def test_scrape_board_oldest_first_with_cutoff(self, mock_fetch, mock_scrape_thread):
        from scraper.philaforum_scraper import save_last_updated, parse_iso_datetime, load_last_updated
        # Page 1 has total pages = 2
        page1_html = """
        <html>
        <woltlab-core-pagination count="2"></woltlab-core-pagination>
        <ol id="thread10" class="tabularListColumns messageGroup wbbThread">
            <a href="https://philaforum.com/forum/thread/10/" class="messageGroupLink">Thread 10</a>
            <woltlab-core-date-time date="2020-01-01T00:00:00+00:00"></woltlab-core-date-time>
        </ol>
        </html>
        """
        # Page 2 (oldest page) has threads from 2010 and 2016
        page2_html = """
        <html>
        <woltlab-core-pagination count="2"></woltlab-core-pagination>
        <ol id="thread2" class="tabularListColumns messageGroup wbbThread">
            <a href="https://philaforum.com/forum/thread/2/" class="messageGroupLink">Thread 2 (newer)</a>
            <woltlab-core-date-time date="2016-08-01T00:00:00+00:00"></woltlab-core-date-time>
        </ol>
        <ol id="thread1" class="tabularListColumns messageGroup wbbThread">
            <a href="https://philaforum.com/forum/thread/1/" class="messageGroupLink">Thread 1 (older)</a>
            <woltlab-core-date-time date="2010-01-01T00:00:00+00:00"></woltlab-core-date-time>
        </ol>
        </html>
        """

        def fake_fetch(url):
            if "pageNo=2" in url:
                return page2_html
            return page1_html

        mock_fetch.side_effect = fake_fetch
        mock_scrape_thread.return_value = ["dummy.pdf"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Set cutoff date to 2016-07-01
            rec_dt = parse_iso_datetime("2016-07-01")
            save_last_updated(tmp_dir, rec_dt)

            pdfs = scrape_board(
                board_url="https://philaforum.com/forum/board/54/",
                output_dir=tmp_dir,
                browser_path="dummy_browser",
                oldest_first=True,
                max_articles=1,
                delay=0,
            )

            # Page 2: Thread 1 (2010) is older than 2016-07-01 -> skipped.
            # Thread 2 (2016-08-01) is newer -> processed!
            self.assertEqual(mock_scrape_thread.call_count, 1)
            # last-updated.json should now be updated with Thread 2's date
            updated_dt = load_last_updated(tmp_dir)
            self.assertEqual(updated_dt.year, 2016)
            self.assertEqual(updated_dt.month, 8)

    def test_find_tag_bounds_simple(self):
        from scraper.philaforum_scraper import find_tag_bounds
        html = '<div class="test"><ul class="messageList"><li>Post 1</li><li>Post 2</li></ul></div>'
        bounds = find_tag_bounds(html, "ul", "messageList")
        self.assertIsNotNone(bounds)
        start_tag_start, content_start, closing_start, closing_end = bounds
        self.assertEqual(html[start_tag_start:content_start], '<ul class="messageList">')
        self.assertEqual(html[content_start:closing_start], '<li>Post 1</li><li>Post 2</li>')
        self.assertEqual(html[closing_start:closing_end], '</ul>')

    def test_find_tag_bounds_nested(self):
        from scraper.philaforum_scraper import find_tag_bounds
        html = (
            '<ul class="wbbThreadPostList messageList">'
            '<li>Post 1 with <ul><li>nested item 1</li><li>nested item 2</li></ul> content</li>'
            '<li>Post 2</li>'
            '</ul>'
        )
        bounds = find_tag_bounds(html, "ul", "messageList")
        self.assertIsNotNone(bounds)
        _, content_start, closing_start, _ = bounds
        content = html[content_start:closing_start]
        self.assertIn("nested item 1", content)
        self.assertIn("Post 2", content)
        self.assertTrue(content.endswith("<li>Post 2</li>"))

    def test_find_tag_bounds_not_found(self):
        from scraper.philaforum_scraper import find_tag_bounds
        html = '<div><p>No list here</p></div>'
        self.assertIsNone(find_tag_bounds(html, "ul", "messageList"))

    def test_extract_thread_posts(self):
        from scraper.philaforum_scraper import extract_thread_posts
        page_html = (
            '<html><body>'
            '<ul class="messageList">'
            '<li id="post_10"><article class="wbbPost message">Hello from page 2</article></li>'
            '</ul>'
            '</body></html>'
        )
        posts = extract_thread_posts(page_html)
        self.assertEqual(posts, '<li id="post_10"><article class="wbbPost message">Hello from page 2</article></li>')

    def test_combine_thread_pages_multiple(self):
        from scraper.philaforum_scraper import combine_thread_pages
        base_html = (
            '<html><head><title>Test Thread</title></head><body>'
            '<h1 class="contentTitle">Test</h1>'
            '<ul class="messageList">'
            '<li id="post_1"><article class="wbbPost message">Post 1</article></li>'
            '</ul>'
            '<footer>Footer</footer></body></html>'
        )
        page2_html = (
            '<html><body><ul class="messageList">'
            '<li id="post_2"><article class="wbbPost message">Post 2</article></li>'
            '</ul></body></html>'
        )
        page3_html = (
            '<html><body><ul class="messageList">'
            '<li id="post_3"><article class="wbbPost message">Post 3</article></li>'
            '</ul></body></html>'
        )

        combined = combine_thread_pages(base_html, [page2_html, page3_html])

        self.assertIn('post_1', combined)
        self.assertIn('post_2', combined)
        self.assertIn('post_3', combined)
        # Ensure all posts are placed before </ul>
        self.assertIn('post_2', combined.split('</ul>')[0])
        self.assertIn('post_3', combined.split('</ul>')[0])
        # Ensure footer remains after </ul>
        self.assertIn('<footer>Footer</footer>', combined)

    def test_combine_thread_pages_empty(self):
        from scraper.philaforum_scraper import combine_thread_pages
        base_html = '<html><ul class="messageList"><li>Post 1</li></ul></html>'
        self.assertEqual(combine_thread_pages(base_html, []), base_html)

    def test_combine_thread_pages_fallback(self):
        from scraper.philaforum_scraper import combine_thread_pages
        base_html = '<html><body><main><article class="message">Post 1</article></main></body></html>'
        page2_html = '<html><body><article class="wbbPost message">Post 2</article></body></html>'
        combined = combine_thread_pages(base_html, [page2_html])
        self.assertIn("Post 1", combined)
    def test_boards_registry_load_and_save(self):
        from scraper.philaforum_scraper import (
            load_boards_registry,
            save_boards_registry,
            BOARDS_FILENAME,
            get_default_board,
            set_default_board,
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Initially empty
            reg = load_boards_registry(tmp_dir)
            self.assertEqual(reg, {})

            # Save an entry with _defaults
            test_data = {
                "_defaults": {"board": "dr"},
                "dr": {
                    "name": "Deutsches-Reich-1872-1945",
                    "board_id": "54",
                    "board_url": "https://philaforum.com/forum/board/54-deutsches-reich-1872-1945/",
                    "last_updated": "2026-10-14T12:00:00+00:00",
                    "timestamp": 1791998400.0,
                    "last_thread_url": "https://philaforum.com/forum/thread/100/",
                    "last_thread_title": "Sample Thread",
                },
            }
            save_boards_registry(tmp_dir, test_data)

            # File boards.json exists
            self.assertTrue(os.path.isfile(os.path.join(tmp_dir, BOARDS_FILENAME)))

            # Reload and verify
            loaded = load_boards_registry(tmp_dir)
            self.assertIn("dr", loaded)
            self.assertEqual(loaded["dr"]["name"], "Deutsches-Reich-1872-1945")
            self.assertEqual(loaded["dr"]["board_id"], "54")
            self.assertEqual(get_default_board(loaded), "dr")
            self.assertEqual(loaded["_defaults"]["board"], "dr")

    def test_get_board_language_precedence(self):
        from scraper.philaforum_scraper import get_board_language
        registry = {
            "_defaults": {"lang": "de"},
            "dr": {"name": "Deutsches-Reich", "lang": "de"},
            "france": {"name": "France", "lang": "fr"},
            "neutral": {"name": "Neutral"},
        }

        # 1. Explicit CLI argument takes top precedence
        self.assertEqual(get_board_language(registry, "france", cli_lang="en"), "en")
        self.assertEqual(get_board_language(registry, "dr", cli_lang="es"), "es")

        # 2. Board-specific entry takes precedence over _defaults
        self.assertEqual(get_board_language(registry, "france", cli_lang=None), "fr")

        # 3. Falls back to _defaults if board entry lacks 'lang'
        self.assertEqual(get_board_language(registry, "neutral", cli_lang=None), "de")

        # 4. Falls back to 'de' if neither board nor _defaults has 'lang'
        self.assertEqual(get_board_language({}, "unknown", cli_lang=None), "de")
        self.assertEqual(get_board_language(None, None, cli_lang=None), "de")

    def test_boards_registry_migration_from_threads_json(self):
        from scraper.philaforum_scraper import load_boards_registry
        with tempfile.TemporaryDirectory() as tmp_dir:
            legacy_file = os.path.join(tmp_dir, "threads.json")
            with open(legacy_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "Deutsches-Reich-1872-1945": {
                            "board_id": "54",
                            "board_url": "https://philaforum.com/forum/board/54/",
                            "last_updated": "2026-10-14T12:00:00+00:00",
                        }
                    },
                    f,
                )

            migrated = load_boards_registry(tmp_dir)
            self.assertIn("Deutsches-Reich-1872-1945", migrated)
            self.assertEqual(migrated["Deutsches-Reich-1872-1945"]["name"], "Deutsches-Reich-1872-1945")
            self.assertEqual(migrated.get("_defaults", {}).get("board"), "Deutsches-Reich-1872-1945")

    def test_boards_registry_migration_from_last_updated_json(self):
        from scraper.philaforum_scraper import load_boards_registry
        with tempfile.TemporaryDirectory() as tmp_dir:
            legacy_file = os.path.join(tmp_dir, "last-updated.json")
            with open(legacy_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "last_updated": "2026-10-14T12:00:00+00:00",
                        "timestamp": 1791998400.0,
                        "board_url": "https://philaforum.com/forum/board/54/",
                    },
                    f,
                )

            migrated = load_boards_registry(tmp_dir)
            self.assertIn("Deutsches-Reich-1872-1945", migrated)
            self.assertEqual(migrated["Deutsches-Reich-1872-1945"]["name"], "Deutsches-Reich-1872-1945")
            self.assertEqual(migrated.get("_defaults", {}).get("board"), "Deutsches-Reich-1872-1945")

    def test_get_and_set_default_board(self):
        from scraper.philaforum_scraper import get_default_board, set_default_board
        reg = {}
        self.assertIsNone(get_default_board(reg))

        set_default_board(reg, "dr")
        self.assertEqual(get_default_board(reg), "dr")
        self.assertEqual(reg["_defaults"]["board"], "dr")

        # Also supports legacy 'board_name' or 'name' under _defaults
        reg_legacy = {"_defaults": {"board_name": "legacy-board"}}
        self.assertEqual(get_default_board(reg_legacy), "legacy-board")

        reg_alt = {"_defaults": {"name": "alt-board"}}
        self.assertEqual(get_default_board(reg_alt), "alt-board")

    def test_find_board_entry_lookup_options(self):
        from scraper.philaforum_scraper import find_board_entry
        registry = {
            "_defaults": {"board": "dr"},
            "dr": {
                "name": "Deutsches-Reich-1872-1945",
                "board_id": "54",
                "board_url": "https://philaforum.com/forum/board/54-deutsches-reich-1872-1945/",
                "last_updated": "2026-10-14T12:00:00+00:00",
            },
        }
        # 1. Exact key match
        res = find_board_entry(registry, "dr")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], "dr")

        # 2. Case-insensitive key match
        res = find_board_entry(registry, "DR")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], "dr")

        # 3. Match by 'name' field
        res = find_board_entry(registry, "Deutsches-Reich-1872-1945")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], "dr")

        # 4. Slug match on name
        res = find_board_entry(registry, "deutsches reich 1872-1945")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], "dr")

        # 5. Match by board_id
        res = find_board_entry(registry, "54")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], "dr")

        # 6. Match by board_url
        res = find_board_entry(registry, "https://philaforum.com/forum/board/54-deutsches-reich-1872-1945/")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], "dr")

        # 7. Private metadata keys are ignored
        self.assertIsNone(find_board_entry(registry, "_defaults"))

        # 8. Missing entry
        res = find_board_entry(registry, "NonExistentBoard")
        self.assertIsNone(res)

    def test_neutralize_image_anchors(self):
        from scraper.philaforum_scraper import neutralize_image_anchors
        sample = (
            '<div class="box">'
            '<a href="https://philaforum.com/attachment/100/" class="imageLink"><img src="stamp.jpg"></a>'
            '<a href="https://philaforum.com/user/10/">User Profile</a>'
            '</div>'
        )
        neutralized = neutralize_image_anchors(sample)
        # Image wrapping <a> converted to <span> with href stripped
        self.assertIn('<span class="imageLink"><img src="stamp.jpg"></span>', neutralized)
        self.assertNotIn('href="https://philaforum.com/attachment/100/"', neutralized)
        # Text link preserved
        self.assertIn('<a href="https://philaforum.com/user/10/">User Profile</a>', neutralized)

    def test_extract_board_info_from_url(self):
        from scraper.philaforum_scraper import extract_board_info_from_url
        b_id, slug = extract_board_info_from_url("https://philaforum.com/forum/board/54-deutsches-reich-1872-1945/")
        self.assertEqual(b_id, "54")
        self.assertEqual(slug, "Deutsches-Reich-1872-1945")

        b_id2, slug2 = extract_board_info_from_url("https://philaforum.com/forum/board/99/")
        self.assertEqual(b_id2, "99")
        self.assertEqual(slug2, "Board-99")

    def test_scrape_board_places_pdfs_in_board_folder(self):
        from scraper.philaforum_scraper import scrape_board
        board_html = """
        <html>
        <h1 class="contentTitle">Deutsches Reich 1872–1945</h1>
        <woltlab-core-pagination count="1"></woltlab-core-pagination>
        <a href="https://philaforum.com/forum/thread/100-thread1/" class="messageGroupLink">Thread 1</a>
        </html>
        """
        thread_html = """
        <html>
        <h1 class="contentTitle">Thread 1</h1>
        <ul class="messageList"><li id="p1"><article class="message">Post 1</article></li></ul>
        </html>
        """

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("scraper.philaforum_scraper.fetch_url") as mock_fetch:
                with patch("scraper.philaforum_scraper.render_html_to_pdf") as mock_render:
                    with patch("os.path.getsize", return_value=2048):
                        mock_fetch.side_effect = lambda url: thread_html if "thread" in url else board_html
                        mock_render.return_value = True

                        pdfs = scrape_board(
                            board_url="https://philaforum.com/forum/board/54-deutsches-reich-1872-1945/",
                            output_dir=tmp_dir,
                            browser_path="dummy_browser",
                            delay=0,
                        )

            # PDF should be placed inside tmp_dir/Deutsches-Reich-1872-1945/de/Thread-1.pdf
            self.assertEqual(len(pdfs), 1)
            pdf_path = pdfs[0]
            expected_folder = os.path.join(tmp_dir, "Deutsches-Reich-1872-1945", "de")
            self.assertEqual(os.path.dirname(pdf_path), expected_folder)
            self.assertTrue(pdf_path.endswith("Thread-1.pdf"))

    def test_scrape_board_uses_custom_name_field_for_folder(self):
        from scraper.philaforum_scraper import scrape_board, save_boards_registry
        board_html = """
        <html>
        <woltlab-core-pagination count="1"></woltlab-core-pagination>
        <a href="https://philaforum.com/forum/thread/100-thread1/" class="messageGroupLink">Thread 1</a>
        </html>
        """
        thread_html = """
        <html>
        <h1 class="contentTitle">Thread 1</h1>
        <ul class="messageList"><li id="p1"><article class="message">Post 1</article></li></ul>
        </html>
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Key is "dr", but name is "Deutsches-Reich-1872-1945"
            save_boards_registry(
                tmp_dir,
                {
                    "dr": {
                        "name": "Deutsches-Reich-1872-1945",
                        "board_id": "54",
                        "board_url": "https://philaforum.com/forum/board/54/",
                    }
                },
            )
            with patch("scraper.philaforum_scraper.fetch_url") as mock_fetch:
                with patch("scraper.philaforum_scraper.render_html_to_pdf") as mock_render:
                    with patch("os.path.getsize", return_value=2048):
                        mock_fetch.side_effect = lambda url: thread_html if "thread" in url else board_html
                        mock_render.return_value = True

                        pdfs = scrape_board(
                            board_url="https://philaforum.com/forum/board/54/",
                            output_dir=tmp_dir,
                            browser_path="dummy_browser",
                            board_key="dr",
                            delay=0,
                        )

            self.assertEqual(len(pdfs), 1)
            pdf_path = pdfs[0]
            # Output folder must match the 'name' field, not the 'dr' key, under the language subfolder
            expected_folder = os.path.join(tmp_dir, "Deutsches-Reich-1872-1945", "de")
            self.assertEqual(os.path.dirname(pdf_path), expected_folder)

    @patch("scraper.philaforum_scraper.scrape_board")
    @patch("scraper.philaforum_scraper.find_browser_executable")
    def test_main_uses_default_board_from_boards_json(self, mock_browser, mock_scrape_board):
        from scraper.philaforum_scraper import main, save_boards_registry
        mock_browser.return_value = "dummy_browser"
        mock_scrape_board.return_value = ["dummy.pdf"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_boards_registry(
                tmp_dir,
                {
                    "_defaults": {"board": "dr"},
                    "dr": {
                        "name": "Deutsches-Reich-1872-1945",
                        "board_id": "54",
                        "board_url": "https://philaforum.com/forum/board/54/",
                    },
                },
            )

            with patch("sys.argv", ["philaforum_scraper.py", "--output-dir", tmp_dir]):
                main()

            mock_scrape_board.assert_called_once()
            call_kwargs = mock_scrape_board.call_args[1]
            self.assertEqual(call_kwargs["board_url"], "https://philaforum.com/forum/board/54/")
            self.assertEqual(call_kwargs["board_key"], "dr")

    @patch("scraper.philaforum_scraper.scrape_board")
    @patch("scraper.philaforum_scraper.find_browser_executable")
    def test_main_updates_defaults_board(self, mock_browser, mock_scrape_board):
        from scraper.philaforum_scraper import main, save_boards_registry, load_boards_registry, get_default_board
        mock_browser.return_value = "dummy_browser"
        mock_scrape_board.return_value = ["dummy.pdf"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_boards_registry(
                tmp_dir,
                {
                    "_defaults": {"board": "dr"},
                    "dr": {
                        "name": "Deutsches-Reich-1872-1945",
                        "board_id": "54",
                        "board_url": "https://philaforum.com/forum/board/54/",
                    },
                    "berlin": {
                        "name": "Berlin-1948-1990",
                        "board_id": "60",
                        "board_url": "https://philaforum.com/forum/board/60-berlin/",
                    },
                },
            )

            # Run with --board berlin
            with patch("sys.argv", ["philaforum_scraper.py", "--board", "berlin", "--output-dir", tmp_dir]):
                main()

            reg = load_boards_registry(tmp_dir)
            self.assertEqual(get_default_board(reg), "berlin")
            self.assertEqual(reg["_defaults"]["board"], "berlin")
            self.assertNotIn("board_name", reg["_defaults"])

    def test_get_image_filename(self):
        # WoltLab attachment slugs with hyphenated extension representations
        self.assertEqual(get_image_filename("https://philaforum.com/attachment/1663-1-jpg/"), "1663-1.jpg")
        self.assertEqual(get_image_filename("https://philaforum.com/attachment/1709-scan0062-jpg/"), "1709-scan0062.jpg")
        self.assertEqual(get_image_filename("/attachment/30996-sample-png/?thumbnail=1"), "30996-sample.png")
        self.assertEqual(get_image_filename("/attachment/123-photo-webp/"), "123-photo.webp")
        self.assertEqual(get_image_filename("/attachment/456-animation-gif/"), "456-animation.gif")
        self.assertEqual(get_image_filename("/attachment/789-doc-jpeg/"), "789-doc.jpeg")

        # Attachment with already dotted extension
        self.assertEqual(get_image_filename("https://philaforum.com/attachment/999-scan.png"), "999-scan.png")

        # Attachment with ID only and MIME fallback
        self.assertEqual(get_image_filename("/attachment/500/", mime="image/png"), "500-attachment.png")
        self.assertEqual(get_image_filename("/attachment/501/", mime="image/jpeg"), "501-attachment.jpg")

        # Regular URLs
        self.assertEqual(get_image_filename("https://example.com/images/germania.png?v=2"), "germania.png")
        self.assertEqual(get_image_filename("https://example.com/download/stamp", mime="image/png"), "stamp.png")

    def test_is_decorative_image(self):
        # Smilies & emojis
        self.assertTrue(is_decorative_image("https://philaforum.com/images/smilies/emojione/263a.png"))
        self.assertTrue(is_decorative_image("/emojis/smile.png"))
        self.assertTrue(is_decorative_image("https://philaforum.com/images/pageLogo.png"))
        self.assertTrue(is_decorative_image("https://example.com/pic.png", attrs='class="smiley"'))
        self.assertTrue(is_decorative_image("https://example.com/pic.png", attrs='class="wcEmoji"'))
        self.assertTrue(is_decorative_image("https://example.com/avatar.jpg", attrs='class="userAvatarImage"'))

        # Actual content images / attachments
        self.assertFalse(is_decorative_image("https://philaforum.com/attachment/1663-1-jpg/"))
        self.assertFalse(is_decorative_image("/attachment/1709-scan0062-jpg/"))
        self.assertFalse(is_decorative_image("https://example.com/uploads/stamp_detail.jpg"))

    def test_fetch_and_save_image_with_images_dir(self):
        from scraper.philaforum_scraper import _IMAGE_CACHE
        _IMAGE_CACHE.clear()

        sample_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        mock_resp = MagicMock()
        mock_resp.read.return_value = sample_bytes
        mock_resp.headers.get_content_type.return_value = "image/gif"
        mock_resp.__enter__.return_value = mock_resp

        with tempfile.TemporaryDirectory() as tmp_dir:
            images_dir = os.path.join(tmp_dir, "images")
            with patch("urllib.request.urlopen", return_value=mock_resp):
                data_uri, file_uri = fetch_and_save_image(
                    "https://philaforum.com/attachment/888-sample-gif/",
                    images_dir=images_dir,
                )

            self.assertIsNotNone(data_uri)
            self.assertTrue(data_uri.startswith("data:image/gif;base64,"))
            self.assertIsNotNone(file_uri)
            self.assertTrue(file_uri.startswith("../images/"))
            self.assertTrue(file_uri.endswith("888-sample.gif"))

            # Verify file exists on disk in images_dir
            saved_file = os.path.join(images_dir, "888-sample.gif")
            self.assertTrue(os.path.isfile(saved_file))
            with open(saved_file, "rb") as f:
                self.assertEqual(f.read(), sample_bytes)

            # Test loading from disk without network request when file exists
            _IMAGE_CACHE.clear()
            with patch("urllib.request.urlopen") as mock_network:
                d_uri, f_uri = fetch_and_save_image(
                    "https://philaforum.com/attachment/888-sample-gif/",
                    images_dir=images_dir,
                )
                mock_network.assert_not_called()
                self.assertEqual(d_uri, data_uri)
                self.assertEqual(f_uri, file_uri)

    def test_embed_and_link_images_rewrites_anchors_to_local_file(self):
        sample_html = """
        <a class="messageGroupLink" href="/forum/user/100-user/">User Name</a>
        <a class="embeddedImageLink jsImageViewer" href="https://philaforum.com/attachment/1663-1-jpg/">
            <img class="embeddedImage" src="https://philaforum.com/attachment/1663-1-jpg/?thumbnail=1" width="352" height="198" alt="Stamp">
        </a>
        <img class="embeddedImage" src="https://philaforum.com/attachment/1709-scan-jpg/" width="300" height="200">
        <img class="smiley" src="/images/smilies/emojione/263a.png" alt="Smile">
        """

        mock_data_uri = "data:image/jpeg;base64,QUJD"
        mock_file_uri_1 = "../images/1663-1.jpg"
        mock_file_uri_2 = "../images/1709-scan.jpg"

        def mock_fetch(url, base_url="https://philaforum.com/", images_dir=None, **kwargs):
            if "263a" in url:
                return ("data:image/png;base64,U01JTEU=", None)
            if "1663" in url:
                return (mock_data_uri, mock_file_uri_1 if images_dir else None)
            if "1709" in url:
                return (mock_data_uri, mock_file_uri_2 if images_dir else None)
            return (None, None)

        with patch("scraper.philaforum_scraper.fetch_and_save_image", side_effect=mock_fetch):
            processed = embed_and_link_images(sample_html, images_dir="D:/output/images")

        # 1. Verify user profile anchor is preserved and NOT swallowed
        self.assertIn('<a class="messageGroupLink" href="/forum/user/100-user/">User Name</a>', processed)

        # 2. Verify attachment anchor href is rewritten to local ../images/ URI with target="_blank"
        self.assertIn(f'href="{mock_file_uri_1}"', processed)
        self.assertIn('target="_blank"', processed)
        self.assertNotIn("jsImageViewer", processed)

        # 3. Verify img src is converted to base64 data URI and width/height stripped
        self.assertIn(f'src="{mock_data_uri}"', processed)
        self.assertNotIn('width="352"', processed)
        self.assertNotIn('height="198"', processed)

        # 4. Verify standalone content image is wrapped in local file link
        self.assertIn(f'<a href="{mock_file_uri_2}" target="_blank"', processed)

        # 5. Verify smiley is inlined as Base64 but NOT wrapped in <a> tag
        self.assertIn('src="data:image/png;base64,U01JTEU="', processed)
        self.assertNotIn('href="../images/263a.png"', processed)

    def test_embed_and_link_images_neutralizes_when_no_images_dir(self):
        sample_html = """
        <a class="authorLink" href="/user/123/">Author</a>
        <a class="embeddedImageLink jsImageViewer" href="https://philaforum.com/attachment/1663-1-jpg/">
            <img class="embeddedImage" src="https://philaforum.com/attachment/1663-1-jpg/?thumbnail=1">
        </a>
        """

        def mock_fetch(url, base_url="https://philaforum.com/", images_dir=None, **kwargs):
            return ("data:image/jpeg;base64,QUJD", None)

        with patch("scraper.philaforum_scraper.fetch_and_save_image", side_effect=mock_fetch):
            processed = embed_and_link_images(sample_html, images_dir=None)

        # Preceding user anchor remains intact
        self.assertIn('<a class="authorLink" href="/user/123/">Author</a>', processed)
        # Attachment anchor is neutralized to <span> without href
        self.assertIn("<span", processed)
        self.assertNotIn('href="https://philaforum.com/attachment/1663-1-jpg/"', processed)
        self.assertNotIn('href=""', processed)

    def test_embed_and_link_images_attachment_card_success(self):
        sample_html = """
        <a href="https://philaforum.com/attachment/55224-img-0008-jpg/" class="messageAttachment jsTooltip" title="Datei IMG_0008.jpg herunterladen">
            <span class="messageAttachmentIcon"><fa-icon name="file-image"></fa-icon></span>
            <span class="messageAttachmentFilename">IMG_0008.jpg</span>
            <span class="messageAttachmentMeta">94,73 kB - 505 Downloads</span>
        </a>
        """
        mock_data = "data:image/jpeg;base64,ABC1234"
        mock_file = "file:///D:/output/Bayern/images/55224-img-0008.jpg"

        with patch("scraper.philaforum_scraper.fetch_and_save_image", return_value=(mock_data, mock_file)):
            processed = embed_and_link_images(sample_html, images_dir="D:/output/Bayern/images")

        # Verifies image preview is injected into the card and link points to local file
        self.assertIn(f'src="{mock_data}"', processed)
        self.assertIn(f'href="{mock_file}"', processed)
        self.assertIn('target="_blank"', processed)
        self.assertIn('IMG_0008.jpg', processed)

    def test_embed_and_link_images_attachment_card_unauthorized_neutralized(self):
        sample_html = """
        <a href="https://philaforum.com/attachment/55224-img-0008-jpg/" class="messageAttachment jsTooltip" title="Datei IMG_0008.jpg herunterladen">
            <span class="messageAttachmentIcon"><fa-icon name="file-image"></fa-icon></span>
            <span class="messageAttachmentFilename">IMG_0008.jpg</span>
            <span class="messageAttachmentMeta">94,73 kB - 505 Downloads</span>
        </a>
        """
        # When unauthenticated (HTTP 403), fetch_and_save_image returns (None, None)
        with patch("scraper.philaforum_scraper.fetch_and_save_image", return_value=(None, None)):
            processed = embed_and_link_images(sample_html, images_dir="D:/output/Bayern/images")

        # Verifies remote href is stripped and element is neutralized to <span>
        self.assertIn("<span", processed)
        self.assertNotIn('href="https://philaforum.com/attachment/55224-img-0008-jpg/"', processed)
        self.assertIn('title="Protected attachment (Login required)"', processed)
        self.assertIn('IMG_0008.jpg', processed)

    def test_parse_arguments_cookie_support(self):
        args = parse_arguments(["--cookie", "test_session=abc; XSRF=123"])
        self.assertEqual(args.cookie, "test_session=abc; XSRF=123")

        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("cookie_from_file=xyz")
            cookie_path = f.name
        try:
            args_file = parse_arguments(["--cookie-file", cookie_path])
            self.assertEqual(args_file.cookie_file, cookie_path)
        finally:
            if os.path.exists(cookie_path):
                os.remove(cookie_path)

    def test_fetch_url_sends_cookie(self):
        import scraper.philaforum_scraper as scraper_module
        old_cookie = scraper_module.COOKIE
        try:
            scraper_module.COOKIE = "wsc30_user_session=token123"
            with patch("urllib.request.urlopen") as mock_open:
                mock_resp = MagicMock()
                mock_resp.read.return_value = b"<html>OK</html>"
                mock_open.return_value.__enter__.return_value = mock_resp

                scraper_module.fetch_url("https://philaforum.com/forum/")

                mock_open.assert_called_once()
                req = mock_open.call_args[0][0]
                self.assertEqual(req.headers.get("Cookie"), "wsc30_user_session=token123")
        finally:
            scraper_module.COOKIE = old_cookie

    def test_embed_and_link_images_inline_attachment_link_with_hyphen_extension(self):
        sample_html = '<p><a href="https://philaforum.com/attachment/413913-1-jpg/">1.jpg</a></p>'
        mock_data = "data:image/jpeg;base64,INLINE_IMAGE_DATA"
        mock_file = "file:///D:/output/Bayern/images/413913-1.jpg"

        with patch("scraper.philaforum_scraper.fetch_and_save_image", return_value=(mock_data, mock_file)):
            processed = embed_and_link_images(sample_html, images_dir="D:/output/Bayern/images")

        self.assertIn(f'src="{mock_data}"', processed)
        self.assertIn(f'href="{mock_file}"', processed)
        self.assertIn("1.jpg", processed)

    def test_embed_and_link_images_inline_attachment_forbidden_neutralized(self):
        sample_html = '<p><a href="https://philaforum.com/attachment/431708-img893-jpg/">img893.jpg</a></p>'
        with patch("scraper.philaforum_scraper.fetch_and_save_image", return_value=(None, None)):
            processed = embed_and_link_images(sample_html, images_dir="D:/output/Bayern/images")

        self.assertIn("<span", processed)
        self.assertNotIn('href="https://philaforum.com/attachment/431708-img893-jpg/"', processed)
        self.assertIn("img893.jpg", processed)
        self.assertIn('title="Protected attachment (Login required)"', processed)

    def test_parse_cookie_input_raw_string(self):
        from scraper.philaforum_scraper import parse_cookie_input
        raw = "wcf21_userID=4350; wcf21_password=secret123"
        self.assertEqual(parse_cookie_input(raw), "wcf21_userID=4350; wcf21_password=secret123")

    def test_parse_cookie_input_with_cookie_prefix(self):
        from scraper.philaforum_scraper import parse_cookie_input
        raw = "Cookie: wcf21_userID=4350; wcf21_password=secret123"
        self.assertEqual(parse_cookie_input(raw), "wcf21_userID=4350; wcf21_password=secret123")

    def test_parse_cookie_input_netscape_format(self):
        from scraper.philaforum_scraper import parse_cookie_input
        netscape_content = (
            "# Netscape HTTP Cookie File\n"
            "# http://curl.haxx.se/rfc/cookie_spec.html\n"
            ".philaforum.com\tTRUE\t/\tFALSE\t1792072027\twcf21_userID\t4350\n"
            ".philaforum.com\tTRUE\t/\tFALSE\t1792072027\twcf21_password\tabc999\n"
        )
        self.assertEqual(
            parse_cookie_input(netscape_content),
            "wcf21_userID=4350; wcf21_password=abc999",
        )

    def test_parse_cookie_input_multiline_pairs(self):
        from scraper.philaforum_scraper import parse_cookie_input
        multiline = "wcf21_userID=4350\nwcf21_password=abc999\n"
        self.assertEqual(
            parse_cookie_input(multiline),
            "wcf21_userID=4350; wcf21_password=abc999",
        )

    def test_render_html_to_pdf_adaptive_timeout(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = os.path.join(tmp_dir, "test.pdf")
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                with patch("os.path.isfile", return_value=True), patch("os.path.getsize", return_value=500):
                    # Short content should get minimum 300s timeout
                    res = render_html_to_pdf("<html>small</html>", pdf_path, "dummy_browser")
                    self.assertTrue(res)
                    self.assertEqual(mock_run.call_args[1]["timeout"], 300)

                    # 10 MB content should scale up: 300 + 10 * 30 = 600s
                    large_content = "x" * (10 * 1024 * 1024)
                    res_large = render_html_to_pdf(large_content, pdf_path, "dummy_browser")
                    self.assertTrue(res_large)
                    self.assertEqual(mock_run.call_args[1]["timeout"], 600)

    def test_render_html_to_pdf_explicit_timeout(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = os.path.join(tmp_dir, "test.pdf")
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                with patch("os.path.isfile", return_value=True), patch("os.path.getsize", return_value=500):
                    res = render_html_to_pdf("<html>test</html>", pdf_path, "dummy_browser", timeout=900)
                    self.assertTrue(res)
                    self.assertEqual(mock_run.call_args[1]["timeout"], 900)

    def test_render_html_to_pdf_timeout_expired_handled(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = os.path.join(tmp_dir, "test.pdf")
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="chrome", timeout=60)):
                res = render_html_to_pdf("<html>huge</html>", pdf_path, "dummy_browser")
                # Must not raise exception, returns False gracefully
                self.assertFalse(res)

    def test_parse_arguments_render_timeout(self):
        args = parse_arguments(["--render-timeout", "450"])
        self.assertEqual(args.render_timeout, 450)


    def test_sanitize_thread_html_attachment_image_scaling_styles(self):
        """Verify that sanitize_thread_html injects CSS rules preventing attachment cards from squeezing images."""
        sample_html = "<html><head><title>Test</title></head><body><p>Content</p></body></html>"
        sanitized = sanitize_thread_html(sample_html)
        self.assertIn(".messageAttachmentList", sanitized)
        self.assertIn(".messageAttachment", sanitized)
        self.assertIn(".attachmentImagePreview", sanitized)
        self.assertIn("max-height: 850px", sanitized)
        self.assertIn("grid-template-columns: none !important", sanitized)

    def test_process_attachment_card_image_styling(self):
        """Verify that attachment card preview images receive max-height 850px and margin auto styling."""
        sample_html = (
            '<ul class="messageAttachmentList">'
            '<li><a href="https://philaforum.com/attachment/12345-stamp-jpg/" class="messageAttachment">'
            '<span class="filename">stamp.jpg</span>'
            '</a></li></ul>'
        )
        with patch("scraper.philaforum_scraper.fetch_and_save_image", return_value=("data:image/jpeg;base64,abc", "file:///D:/images/stamp.jpg")):
            processed = embed_and_link_images(sample_html, images_dir="D:/images")

        self.assertIn('class="attachmentImagePreview"', processed)
        self.assertIn('max-height:850px', processed)
        self.assertIn('margin:0 auto;', processed)

    def test_transliterate_german(self):
        from scraper.philaforum_scraper import transliterate_german
        self.assertEqual(transliterate_german("pärchen"), "paerchen")
        self.assertEqual(transliterate_german("völkersbach"), "voelkersbach")
        self.assertEqual(transliterate_german("düsseldorf"), "duesseldorf")
        self.assertEqual(transliterate_german("Groß"), "Gross")
        self.assertEqual(transliterate_german("p%C3%A4rchendr"), "paerchendr")
        self.assertEqual(transliterate_german("%C3%BCber"), "ueber")
        self.assertEqual(transliterate_german(""), "")

    def test_get_image_filename_with_percent_encoded_and_umlauts(self):
        from scraper.philaforum_scraper import get_image_filename
        # WoltLab attachment with %C3%BCber
        fn1 = get_image_filename(
            "https://philaforum.com/attachment/413363-dr-158-pos-65-farbpunkte-%C3%BCber-dem-feld-mit-dem-lorbeer-jpg/"
        )
        self.assertEqual(fn1, "413363-dr-158-pos-65-farbpunkte-ueber-dem-feld-mit-dem-lorbeer.jpg")

        # WoltLab attachment with %C3%A4 (ä)
        fn2 = get_image_filename("https://philaforum.com/attachment/101437-p%C3%A4rchendr-jpg/")
        self.assertEqual(fn2, "101437-paerchendr.jpg")

        # Direct path with umlaut
        fn3 = get_image_filename("https://philaforum.com/images/schöne-marke.png")
        self.assertEqual(fn3, "schoene-marke.png")

    def test_network_rate_limiter_sequential(self):
        limiter = NetworkRateLimiter(min_interval=0.05)
        t0 = time.time()
        limiter.wait()
        limiter.wait()
        elapsed = time.time() - t0
        self.assertGreaterEqual(elapsed, 0.04)

    def test_network_rate_limiter_concurrent(self):
        limiter = NetworkRateLimiter(min_interval=0.04)
        timestamps = []
        lock = threading.Lock()

        def worker():
            limiter.wait()
            with lock:
                timestamps.append(time.time())

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(timestamps), 3)
        timestamps.sort()
        for i in range(len(timestamps) - 1):
            self.assertGreaterEqual(timestamps[i + 1] - timestamps[i], 0.025)

    def test_parse_arguments_workers_default(self):
        args = parse_arguments([])
        self.assertEqual(args.workers, 1)

    def test_parse_arguments_workers_custom(self):
        args = parse_arguments(["--workers", "4"])
        self.assertEqual(args.workers, 4)

    def test_scrape_board_with_workers_parallel(self):
        board_html = """
        <html>
          <woltlab-core-pagination page="1" count="1" url="https://philaforum.com/forum/board/54/?pageNo=%d"></woltlab-core-pagination>
          <ol class="messageGroupList">
            <li class="messageGroup"><a href="https://philaforum.com/forum/thread/101-alpha/" class="messageGroupLink">Alpha</a><time datetime="2026-01-01T10:00:00Z"></time></li>
            <li class="messageGroup"><a href="https://philaforum.com/forum/thread/102-beta/" class="messageGroupLink">Beta</a><time datetime="2026-01-01T11:00:00Z"></time></li>
            <li class="messageGroup"><a href="https://philaforum.com/forum/thread/103-gamma/" class="messageGroupLink">Gamma</a><time datetime="2026-01-01T12:00:00Z"></time></li>
          </ol>
        </html>
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("scraper.philaforum_scraper.fetch_url", return_value=board_html), \
                 patch("scraper.philaforum_scraper.scrape_thread", side_effect=lambda **kwargs: [f"{kwargs.get('thread_title', 'T')}.pdf"]):
                pdfs = scrape_board(
                    board_url="https://philaforum.com/forum/board/54-deutsches-reich/",
                    output_dir=tmp_dir,
                    browser_path="dummy_browser",
                    workers=2,
                    delay=0.0,
                )
                self.assertEqual(pdfs, ["Alpha.pdf", "Beta.pdf", "Gamma.pdf"])

    def test_scrape_board_oldest_first_with_workers(self):
        board_html = """
        <html>
          <woltlab-core-pagination page="1" count="1" url="https://philaforum.com/forum/board/54/?pageNo=%d"></woltlab-core-pagination>
          <ol class="messageGroupList">
            <li class="messageGroup"><a href="https://philaforum.com/forum/thread/101-newer/" class="messageGroupLink">Newer</a><time datetime="2026-01-02T10:00:00Z"></time></li>
            <li class="messageGroup"><a href="https://philaforum.com/forum/thread/102-older/" class="messageGroupLink">Older</a><time datetime="2026-01-01T10:00:00Z"></time></li>
          </ol>
        </html>
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("scraper.philaforum_scraper.fetch_url", return_value=board_html), \
                 patch("scraper.philaforum_scraper.scrape_thread", side_effect=lambda **kwargs: [f"{kwargs.get('thread_title', 'T')}.pdf"]):
                pdfs = scrape_board(
                    board_url="https://philaforum.com/forum/board/54-deutsches-reich/",
                    output_dir=tmp_dir,
                    browser_path="dummy_browser",
                    oldest_first=True,
                    workers=2,
                    delay=0.0,
                )
                # In oldest_first, the older thread (index 1 reversed to index 0) is processed first
                self.assertEqual(pdfs, ["Older.pdf", "Newer.pdf"])

    def test_scrape_board_immediate_exit_when_up_to_date(self):
        """Verify that scrape_board exits immediately when page 1 top thread is older than cutoff."""
        from scraper.philaforum_scraper import save_boards_registry
        board_html = """
        <html>
          <woltlab-core-pagination page="1" count="5" url="https://philaforum.com/forum/board/54/?pageNo=%d"></woltlab-core-pagination>
          <ol id="thread101" class="tabularListColumns messageGroup wbbThread">
            <a href="https://philaforum.com/forum/thread/101-sample/" class="messageGroupLink">Sample</a>
            <woltlab-core-date-time date="2026-01-01T10:00:00+00:00"></woltlab-core-date-time>
          </ol>
        </html>
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Set last_updated to 2026-01-02 (newer than page 1 thread from 2026-01-01)
            registry = {
                "Deutsches-Reich-1872-1945": {
                    "board_url": "https://philaforum.com/forum/board/54-deutsches-reich/",
                    "last_updated": "2026-01-02T10:00:00+00:00",
                    "name": "Deutsches-Reich-1872-1945",
                }
            }
            save_boards_registry(tmp_dir, registry)

            scrape_calls = []
            with patch("scraper.philaforum_scraper.fetch_url", return_value=board_html), \
                 patch("scraper.philaforum_scraper.scrape_thread", side_effect=lambda **kwargs: scrape_calls.append(kwargs)):
                pdfs = scrape_board(
                    board_url="https://philaforum.com/forum/board/54-deutsches-reich/",
                    output_dir=tmp_dir,
                    browser_path="dummy_browser",
                    delay=0.0,
                )
                self.assertEqual(pdfs, [])
                self.assertEqual(len(scrape_calls), 0)

    def test_scrape_board_oldest_first_fast_forward_binary_search(self):
        """Verify that oldest_first binary searches the page range to find the oldest page containing updates."""
        from scraper.philaforum_scraper import save_boards_registry

        # Page 1 (2026-01-03), Page 2 (2026-01-02), Page 3 (2026-01-01)
        p1 = '<html><woltlab-core-pagination count="3"></woltlab-core-pagination><ol id="thread1" class="messageGroup"><a href="https://philaforum.com/forum/thread/1/" class="messageGroupLink">T1</a><woltlab-core-date-time date="2026-01-03T00:00:00+00:00"></woltlab-core-date-time></ol></html>'
        p2 = '<html><woltlab-core-pagination count="3"></woltlab-core-pagination><ol id="thread2" class="messageGroup"><a href="https://philaforum.com/forum/thread/2/" class="messageGroupLink">T2</a><woltlab-core-date-time date="2026-01-02T00:00:00+00:00"></woltlab-core-date-time></ol></html>'
        p3 = '<html><woltlab-core-pagination count="3"></woltlab-core-pagination><ol id="thread3" class="messageGroup"><a href="https://philaforum.com/forum/thread/3/" class="messageGroupLink">T3</a><woltlab-core-date-time date="2026-01-01T00:00:00+00:00"></woltlab-core-date-time></ol></html>'

        pages_fetched = []
        def mock_fetch(url):
            pages_fetched.append(url)
            if "pageNo=3" in url:
                return p3
            elif "pageNo=2" in url:
                return p2
            return p1

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Cutoff is 2026-01-01T12:00:00. Page 3 has thread from 2026-01-01T00:00:00 (older than cutoff).
            # Page 2 has thread from 2026-01-02 (newer than cutoff).
            registry = {
                "Deutsches-Reich-1872-1945": {
                    "board_url": "https://philaforum.com/forum/board/54-deutsches-reich/",
                    "last_updated": "2026-01-01T12:00:00+00:00",
                    "name": "Deutsches-Reich-1872-1945",
                }
            }
            save_boards_registry(tmp_dir, registry)

            with patch("scraper.philaforum_scraper.fetch_url", side_effect=mock_fetch), \
                 patch("scraper.philaforum_scraper.scrape_thread", side_effect=lambda **kwargs: [f"{kwargs.get('thread_title', 'T')}.pdf"]):
                pdfs = scrape_board(
                    board_url="https://philaforum.com/forum/board/54-deutsches-reich/",
                    output_dir=tmp_dir,
                    browser_path="dummy_browser",
                    oldest_first=True,
                    delay=0.0,
                )
                # Should process Page 2 (T2) then Page 1 (T1) in oldest-first order
                self.assertEqual(pdfs, ["T2.pdf", "T1.pdf"])

    def test_boards_registry_records_last_pdf_after_writing(self):
        """Verify that boards.json records last_pdf only after document is successfully generated."""
        from scraper.philaforum_scraper import load_boards_registry

        board_html = """
        <html>
          <woltlab-core-pagination count="1"></woltlab-core-pagination>
          <ol id="thread1" class="messageGroup">
            <a href="https://philaforum.com/forum/thread/101/" class="messageGroupLink">Sample Thread</a>
            <woltlab-core-date-time date="2026-05-01T12:00:00+00:00"></woltlab-core-date-time>
          </ol>
        </html>
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Case 1: PDF generation succeeds -> last_pdf is recorded
            with patch("scraper.philaforum_scraper.fetch_url", return_value=board_html), \
                 patch("scraper.philaforum_scraper.scrape_thread", return_value=["D:/out/Sample-Thread.pdf"]):
                scrape_board(
                    board_url="https://philaforum.com/forum/board/54-deutsches-reich-1872-1945/",
                    output_dir=tmp_dir,
                    browser_path="dummy_browser",
                    delay=0.0,
                )
            reg = load_boards_registry(tmp_dir)
            from scraper.philaforum_scraper import find_board_entry
            matched = find_board_entry(reg, "54")
            self.assertIsNotNone(matched)
            entry = matched[1]
            self.assertEqual(entry.get("last_pdf"), "Sample-Thread.pdf")
            self.assertEqual(entry.get("last_thread_title"), "Sample Thread")

    def test_get_pdf_page_count(self):
        from scraper.philaforum_scraper import get_pdf_page_count
        with tempfile.TemporaryDirectory() as tmp_dir:
            non_existent = os.path.join(tmp_dir, "missing.pdf")
            self.assertEqual(get_pdf_page_count(non_existent), 0)

            # Test regex binary fallback
            dummy_pdf = os.path.join(tmp_dir, "dummy.pdf")
            with open(dummy_pdf, "wb") as f:
                f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Page >>\nendobj\n2 0 obj\n<< /Type /Page >>\nendobj\n3 0 obj\n<< /Type /Page >>\nendobj\n%%EOF")
            self.assertEqual(get_pdf_page_count(dummy_pdf), 3)

    def test_split_message_list_posts(self):
        from scraper.philaforum_scraper import split_message_list_posts
        # Case 1: Simple posts
        content = '<li id="post_1"><p>Post 1</p></li><li id="post_2"><p>Post 2</p></li>'
        posts = split_message_list_posts(content)
        self.assertEqual(len(posts), 2)
        self.assertIn("Post 1", posts[0])
        self.assertIn("Post 2", posts[1])

        # Case 2: Nested list inside a post
        nested_content = (
            '<li id="post_1">'
            '<p>Post with bullets:</p>'
            '<ul><li>Bullet A</li><li>Bullet B</li></ul>'
            '</li>'
            '<li id="post_2"><p>Post 2</p></li>'
        )
        nested_posts = split_message_list_posts(nested_content)
        self.assertEqual(len(nested_posts), 2)
        self.assertIn("Bullet A", nested_posts[0])
        self.assertIn("Bullet B", nested_posts[0])
        self.assertIn("Post 2", nested_posts[1])

        # Case 3: Fallback to <article class="...message..."> elements
        article_content = (
            '<article class="wbbPost message">Article 1</article>'
            '<article class="wbbPost message">Article 2</article>'
        )
        article_posts = split_message_list_posts(article_content)
        self.assertEqual(len(article_posts), 2)
        self.assertEqual(article_posts[0], '<article class="wbbPost message">Article 1</article>')

        # Case 4: Empty string
        self.assertEqual(split_message_list_posts(""), [])

    def test_split_thread_posts(self):
        from scraper.philaforum_scraper import split_thread_posts
        doc = (
            '<!DOCTYPE html><html><head><title>Title</title></head><body>'
            '<header>Header Content</header>'
            '<ul class="wbbThreadPostList messageList">'
            '<li id="post_1"><p>First post</p></li>'
            '<li id="post_2"><p>Second post</p></li>'
            '</ul>'
            '<footer>Footer Content</footer></body></html>'
        )
        header_html, posts, footer_html = split_thread_posts(doc)
        self.assertIn('<header>Header Content</header>', header_html)
        self.assertIn('<ul class="wbbThreadPostList messageList">', header_html)
        self.assertEqual(len(posts), 2)
        self.assertIn('First post', posts[0])
        self.assertIn('Second post', posts[1])
        self.assertTrue(footer_html.startswith('</ul>'))
        self.assertIn('<footer>Footer Content</footer>', footer_html)

    def test_assemble_part_html(self):
        from scraper.philaforum_scraper import assemble_part_html
        header = '<html><body><ul class="messageList">'
        footer = '</ul></body></html>'
        posts = ['<li id="p1">Post 1</li>']

        # Part 1 with link to Part 2
        p1_html = assemble_part_html(
            header_html=header,
            posts=posts,
            footer_html=footer,
            next_pdf_filename="Thread-Part2.pdf",
            prev_pdf_filename=None,
            part_index=1,
        )
        self.assertIn('Fortsetzung in / Continued in:', p1_html)
        self.assertIn('<a href="Thread-Part2.pdf"', p1_html)
        self.assertNotIn('prevPartLink', p1_html)

        # Part 2 with link back to Part 1 and link forward to Part 3
        p2_html = assemble_part_html(
            header_html=header,
            posts=['<li id="p2">Post 2</li>'],
            footer_html=footer,
            next_pdf_filename="Thread-Part3.pdf",
            prev_pdf_filename="Thread.pdf",
            part_index=2,
        )
        self.assertIn('Teil 2 / Part 2', p2_html)
        self.assertIn('<a href="Thread.pdf"', p2_html)
        self.assertIn('Fortsetzung in / Continued in:', p2_html)
        self.assertIn('<a href="Thread-Part3.pdf"', p2_html)

        # Final Part with link back to Part 2 and no next link
        p3_html = assemble_part_html(
            header_html=header,
            posts=['<li id="p3">Post 3</li>'],
            footer_html=footer,
            next_pdf_filename=None,
            prev_pdf_filename="Thread-Part2.pdf",
            part_index=3,
        )
        self.assertIn('Teil 3 / Part 3', p3_html)
        self.assertIn('<a href="Thread-Part2.pdf"', p3_html)
        self.assertNotIn('nextPartLink', p3_html)

    def test_scrape_thread_multipart_splitting(self):
        from scraper.philaforum_scraper import scrape_thread
        thread_html = (
            '<html><head><title>Test Thread - Forum</title></head><body>'
            '<h1 class="contentTitle">Test Thread</h1>'
            '<ul class="messageList">'
            '<li id="post_1"><article class="message"><p>Post 1 Content</p></article></li>'
            '<li id="post_2"><article class="message"><p>Post 2 Content</p></article></li>'
            '<li id="post_3"><article class="message"><p>Post 3 Content</p></article></li>'
            '</ul></body></html>'
        )

        rendered_docs = []

        def fake_render(html_content, output_pdf_path, browser_path, temp_dir=None, timeout=None):
            rendered_docs.append((output_pdf_path, html_content))
            with open(output_pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 dummy content")
            return True

        def fake_page_count(pdf_path):
            # Inspect the recorded HTML for this PDF to return simulated page count
            matching = [html for path, html in rendered_docs if path == pdf_path]
            content = matching[-1] if matching else ""
            # If all 3 posts are present, return 3 pages (> 2 max)
            if "Post 1" in content and "Post 2" in content and "Post 3" in content:
                return 3
            # If 2 posts are present, return 2 pages (<= 2 max)
            elif "Post 1" in content and "Post 2" in content:
                return 2
            # 1 post returns 1 page
            return 1

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("scraper.philaforum_scraper.fetch_url", return_value=thread_html), \
                 patch("scraper.philaforum_scraper.render_html_to_pdf", side_effect=fake_render), \
                 patch("scraper.philaforum_scraper.get_pdf_page_count", side_effect=fake_page_count):

                res = scrape_thread(
                    thread_url="https://philaforum.com/forum/thread/100-test-thread/",
                    output_dir=tmp_dir,
                    browser_path="dummy_browser",
                    max_pdf_pages=2,
                )

                # Expect 2 files: Test-Thread.pdf and Test-Thread-Part2.pdf
                self.assertEqual(len(res), 2)
                base_pdf = os.path.basename(res[0])
                part2_pdf = os.path.basename(res[1])
                self.assertEqual(base_pdf, "Test-Thread.pdf")
                self.assertEqual(part2_pdf, "Test-Thread-Part2.pdf")

                # Both files must physically exist on disk
                self.assertTrue(os.path.isfile(res[0]))
                self.assertTrue(os.path.isfile(res[1]))

                # Verify Part 1 HTML sent to render contains link to Part 2 and retains title
                p1_candidates = [html for path, html in rendered_docs if "Test-Thread-Part2.pdf" in html]
                self.assertTrue(len(p1_candidates) > 0)
                final_p1_html = p1_candidates[-1]
                self.assertIn("Test-Thread-Part2.pdf", final_p1_html)
                self.assertIn('<h1 class="contentTitle">Test Thread</h1>', final_p1_html)

                # Verify Part 2 HTML sent to render contains link back to Part 1 and retains title
                p2_renders = [html for path, html in rendered_docs if path == res[1]]
                self.assertTrue(len(p2_renders) > 0)
                final_p2_html = p2_renders[-1]
                self.assertIn("Test-Thread.pdf", final_p2_html)
                self.assertIn('<h1 class="contentTitle">Test Thread</h1>', final_p2_html)

    def test_scrape_thread_single_post_oversized(self):
        from scraper.philaforum_scraper import scrape_thread
        single_post_html = (
            '<html><head><title>Oversized Post - Forum</title></head><body>'
            '<h1 class="contentTitle">Oversized Post</h1>'
            '<ul class="messageList">'
            '<li id="post_1"><article class="message"><p>Very long single post</p></article></li>'
            '</ul></body></html>'
        )

        def fake_render(html_content, output_pdf_path, browser_path, temp_dir=None, timeout=None):
            with open(output_pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 dummy")
            return True

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("scraper.philaforum_scraper.fetch_url", return_value=single_post_html), \
                 patch("scraper.philaforum_scraper.render_html_to_pdf", side_effect=fake_render), \
                 patch("scraper.philaforum_scraper.get_pdf_page_count", return_value=10):  # 10 pages > max 2

                res = scrape_thread(
                    thread_url="https://philaforum.com/forum/thread/200-oversized-post/",
                    output_dir=tmp_dir,
                    browser_path="dummy_browser",
                    max_pdf_pages=2,
                )

                # Single post cannot be broken; must remain single file
                self.assertEqual(len(res), 1)
                self.assertEqual(os.path.basename(res[0]), "Oversized-Post.pdf")

    def test_scrape_thread_within_limit_no_split(self):
        from scraper.philaforum_scraper import scrape_thread
        thread_html = (
            '<html><head><title>Small Thread - Forum</title></head><body>'
            '<h1 class="contentTitle">Small Thread</h1>'
            '<ul class="messageList">'
            '<li id="post_1"><article class="message"><p>Post 1</p></article></li>'
            '<li id="post_2"><article class="message"><p>Post 2</p></article></li>'
            '</ul></body></html>'
        )

        render_count = 0
        def fake_render(html_content, output_pdf_path, browser_path, temp_dir=None, timeout=None):
            nonlocal render_count
            render_count += 1
            with open(output_pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 dummy")
            return True

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("scraper.philaforum_scraper.fetch_url", return_value=thread_html), \
                 patch("scraper.philaforum_scraper.render_html_to_pdf", side_effect=fake_render), \
                 patch("scraper.philaforum_scraper.get_pdf_page_count", return_value=5):  # 5 pages <= 50 max

                res = scrape_thread(
                    thread_url="https://philaforum.com/forum/thread/300-small-thread/",
                    output_dir=tmp_dir,
                    browser_path="dummy_browser",
                    max_pdf_pages=50,
                )

                self.assertEqual(len(res), 1)
                self.assertEqual(os.path.basename(res[0]), "Small-Thread.pdf")
                # Exactly 1 render call, zero splitting overhead
                self.assertEqual(render_count, 1)


if __name__ == "__main__":
    unittest.main()

