#!/usr/bin/env python3
"""
Unit tests for philaforum_scraper.py
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Ensure src/main/python is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../main/python")))

from scraper.philaforum_scraper import (
    DEFAULT_BOARD_URL,
    extract_pagination_count,
    extract_threads_from_board,
    find_browser_executable,
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

        # Verify <base href="..."> is injected
        self.assertIn('<base href="https://philaforum.com/">', sanitized)

        # Verify thumbnail upgrade
        self.assertNotIn("?thumbnail=1", sanitized)
        self.assertIn("https://philaforum.com/attachment/30996-sample-jpg", sanitized)

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

    def test_parse_arguments(self):
        # Test defaults
        args = parse_arguments([])
        self.assertEqual(args.board_url, DEFAULT_BOARD_URL)
        self.assertFalse(args.first_page_only)
        self.assertIsNone(args.thread_url)
        self.assertIsNone(args.max_threads)
        self.assertIsNone(args.max_pages)

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

        # Limited to 2 pages
        self.assertEqual(len(pdfs), 2)
        self.assertEqual(mock_fetch.call_count, 2)

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


if __name__ == "__main__":
    unittest.main()
