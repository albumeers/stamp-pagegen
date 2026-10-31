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
Unit Tests for Philaforum Pure HTML Scraper and Translator Pipeline.
Tests direct HTML scraping, image downloading with relative references,
Ollama-powered translation, and resume tracking via boards.json and translation.json.
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Ensure src/main/python is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../main/python")))

from philaforum.scraper import (
    NetworkRateLimiter,
    combine_thread_pages,
    embed_and_link_images,
    extract_board_info_from_url,
    extract_pagination_count,
    extract_thread_posts,
    extract_threads_from_board,
    fetch_and_save_image,
    fetch_url,
    find_board_entry,
    get_image_filename,
    is_decorative_image,
    load_boards_registry,
    parse_cookie_input,
    parse_iso_datetime,
    prune_unwanted_html_elements,
    remove_tag_blocks,
    remove_wcf13_footer,
    sanitize_filename,
    sanitize_thread_html,
    sanitize_title_slug,
    save_boards_registry,
    scrape_board,
    scrape_thread,
    transliterate_german,
)
from util.translation import (
    clean_translated_text,
    load_translation_registry,
    query_ollama_translation,
    record_translation_in_registry,
    resolve_registry_path,
    save_translation_registry,
    translate_forum_directory,
    translate_post_text,
    translate_single_html_file,
    translate_thread_html,
    update_image_links_to_root,
)


class TestPhilaforumScraperPureHtml(unittest.TestCase):
    """Test suite for philaforum.scraper functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_board_info_from_url(self):
        url = "https://philaforum.com/forum/board/241-l%C3%BCbeck/"
        board_id, slug = extract_board_info_from_url(url)
        self.assertEqual(board_id, "241")
        self.assertEqual(slug, "Luebeck")

        url2 = "https://philaforum.com/forum/board/54-deutsches-reich-1872-1945/"
        board_id2, slug2 = extract_board_info_from_url(url2)
        self.assertEqual(board_id2, "54")
        self.assertEqual(slug2, "Deutsches-Reich-1872-1945")

        url3 = "https://philaforum.com/forum/board/999/"
        board_id3, slug3 = extract_board_info_from_url(url3)
        self.assertEqual(board_id3, "999")
        self.assertEqual(slug3, "Board-999")

    def test_transliterate_and_slug(self):
        self.assertEqual(transliterate_german("Lübeck"), "Luebeck")
        self.assertEqual(transliterate_german("Groß-Gera"), "Gross-Gera")
        self.assertEqual(sanitize_title_slug("241-l%C3%BCbeck"), "Luebeck")
        self.assertEqual(sanitize_title_slug("Stempel aus 1872–1945"), "Stempel-aus-1872-1945")
        # & and &amp; replaced with and
        self.assertEqual(sanitize_title_slug("Lübeck & Hamburg"), "Luebeck-and-Hamburg")
        self.assertEqual(sanitize_title_slug("Post &amp; Telegrafie"), "Post-and-Telegrafie")
        self.assertEqual(sanitize_title_slug("Briefmarken&Münzen"), "Briefmarken-and-Muenzen")
        self.assertEqual(sanitize_filename("photo & scan.jpg"), "photo_and_scan.jpg")
        self.assertEqual(sanitize_filename("document &amp; test.png"), "document_and_test.png")

    def test_is_decorative_image(self):
        self.assertTrue(is_decorative_image("https://philaforum.com/images/smilies/emojione/1f600.png"))
        self.assertTrue(is_decorative_image("https://philaforum.com/images/avatars/avatar-12.jpg"))
        self.assertTrue(is_decorative_image("", attrs='class="wbbSmiley"'))
        self.assertFalse(is_decorative_image("https://philaforum.com/forum/attachment/12345-stempel.jpg"))

    def test_get_image_filename(self):
        url = "https://philaforum.com/forum/attachment/12345-l%C3%BCbeck_marke.jpg"
        fname = get_image_filename(url)
        self.assertEqual(fname, "12345-luebeck_marke.jpg")

        url_and = "https://philaforum.com/forum/attachment/9999-brief_%26_karte.jpg"
        fname_and = get_image_filename(url_and)
        self.assertEqual(fname_and, "9999-brief_and_karte.jpg")

    def test_boards_registry_io(self):
        registry = {
            "_defaults": {"board": "Luebeck"},
            "Luebeck": {
                "name": "Luebeck",
                "board_id": "241",
                "board_url": "https://philaforum.com/forum/board/241-l%C3%BCbeck/",
                "last_html": "Luebeck-Postgeschichte.html",
            },
        }
        save_boards_registry(self.temp_dir, registry)
        loaded = load_boards_registry(self.temp_dir)
        self.assertIn("Luebeck", loaded)
        self.assertEqual(loaded["Luebeck"]["board_id"], "241")

        match = find_board_entry(loaded, "241")
        self.assertIsNotNone(match)
        self.assertEqual(match[0], "Luebeck")

    def test_parse_cookie_input_formats(self):
        # 1. Raw string with or without 'Cookie:'
        self.assertEqual(parse_cookie_input("a=1; b=2"), "a=1; b=2")
        self.assertEqual(parse_cookie_input("Cookie: a=1; b=2"), "a=1; b=2")

        # 2. Netscape cookie file
        netscape_content = (
            "# Netscape HTTP Cookie File\n"
            "# https://curl.se/docs/http-cookies.html\n"
            ".philaforum.com\tTRUE\t/\tFALSE\t1792374920\twcf21_userID\t12345\n"
            ".philaforum.com\tTRUE\t/\tFALSE\t1792374920\twcf21_cookie_hash\tabcdef\n"
        )
        netscape_file = os.path.join(self.temp_dir, "netscape_cookies.txt")
        with open(netscape_file, "w", encoding="utf-8") as f:
            f.write(netscape_content)
        self.assertEqual(parse_cookie_input(netscape_file), "wcf21_userID=12345; wcf21_cookie_hash=abcdef")

        # 3. JSON cookie file
        json_content = json.dumps([
            {"name": "wcf21_userID", "value": "999"},
            {"name": "wcf21_session", "value": "xyz"},
        ])
        json_file = os.path.join(self.temp_dir, "cookies.json")
        with open(json_file, "w", encoding="utf-8") as f:
            f.write(json_content)
        self.assertEqual(parse_cookie_input(json_file), "wcf21_userID=999; wcf21_session=xyz")

        # 4. Multi-line name=value file
        multiline_file = os.path.join(self.temp_dir, "multiline.txt")
        with open(multiline_file, "w", encoding="utf-8") as f:
            f.write("user=admin\ntoken=secret\n")
        self.assertEqual(parse_cookie_input(multiline_file), "user=admin; token=secret")

    def test_sanitize_thread_html_styling_and_links(self):
        sample_html = """
        <html>
        <head>
            <title>Originaler Titel</title>
            <base href="https://philaforum.com/">
            <script src="https://philaforum.com/js/WoltLabSuite.Core.min.js?v=1732185324"></script>
        </head>
        <body>
        <div id="pageHeaderContainer">Header</div>
        <div class="contentHeader"><h1 class="contentTitle">Lübeck Briefe</h1></div>
        <ul class="messageList">
            <li class="message">
                <div class="messageSidebar">Author Info</div>
                <div class="messageContent">
                    <div class="messageText">
                        <p>Hier ist ein Bild:</p>
                        <a href="../images/100-stempel.jpg"><img src="../images/100-stempel.jpg" width="800" height="600"></a>
                    </div>
                </div>
            </li>
        </ul>
        <script>var WCF_PATH = 'https://philaforum.com/';</script>
        <div id="pageFooter">Footer</div>
        </body>
        </html>
        """
        sanitized = sanitize_thread_html(sample_html, image_link_prefix="../images/")
        # Base href removed
        self.assertNotIn("<base", sanitized.lower())
        # External and inline scripts removed
        self.assertNotIn("WoltLabSuite.Core.min.js", sanitized)
        self.assertNotIn("WCF_PATH", sanitized)
        # Print stylesheet injected
        self.assertIn('id="scraper-print-stylesheet"', sanitized)
        # Chrome hidden in stylesheet
        self.assertIn("#pageHeaderContainer", sanitized)
        self.assertIn("#wcf13 > div > footer", sanitized)
        self.assertIn(".messageFooterGroup", sanitized)
        self.assertIn('id="scraper-cleanup-wcf"', sanitized)
        self.assertIn("display: none !important;", sanitized)
        # Width/height attributes removed from img
        self.assertNotIn('width="800"', sanitized)

    def test_extract_threads_from_board(self):
        board_html = """
        <ul class="tabularList">
            <li class="tabularListRow">
                <h3 class="wbbTopicLink">
                    <a href="https://philaforum.com/forum/thread/999-luebeck-stempel/">Lübeck Stempel 1860</a>
                </h3>
                <time datetime="2026-03-15T10:00:00Z"></time>
            </li>
            <li class="tabularListRow wbbSticky">
                <h3 class="wbbTopicLink">
                    <a href="https://philaforum.com/forum/thread/888-sticky-thread/">Wichtige Regeln</a>
                </h3>
                <time datetime="2026-01-01T08:00:00Z"></time>
            </li>
        </ul>
        """
        threads = extract_threads_from_board(board_html)
        self.assertEqual(len(threads), 2)
        self.assertEqual(threads[0].title, "Lübeck Stempel 1860")
        self.assertFalse(threads[0].is_sticky)
        self.assertEqual(threads[1].title, "Wichtige Regeln")
        self.assertTrue(threads[1].is_sticky)

    def test_combine_thread_pages(self):
        page1 = """
        <html><body>
        <ul class="messageList">
            <li id="post1"><div class="messageText">Post 1</div></li>
        </ul>
        </body></html>
        """
        page2 = """
        <html><body>
        <ul class="messageList">
            <li id="post2"><div class="messageText">Post 2</div></li>
        </ul>
        </body></html>
        """
        combined = combine_thread_pages(page1, [page2])
        self.assertIn("Post 1", combined)
        self.assertIn("Post 2", combined)
        self.assertIn("Additional Forum Page Posts Appended", combined)

    @patch("urllib.request.urlopen")
    def test_scrape_thread_end_to_end(self, mock_urlopen):
        # Mock HTML responses
        thread_html = """
        <html><head><title>Lübeck Thread</title></head><body>
        <div class="contentHeader"><h1 class="contentTitle">Lübeck Briefe 1865</h1></div>
        <ul class="messageList">
            <li class="message">
                <div class="messageContent">
                    <div class="messageText"><p>Schöner Beleg aus Lübeck.</p></div>
                </div>
            </li>
        </ul>
        </body></html>
        """
        mock_resp = MagicMock()
        mock_resp.read.return_value = thread_html.encode("utf-8")
        mock_resp.headers.get_content_charset.return_value = "utf-8"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = scrape_thread(
            thread_url="https://philaforum.com/forum/thread/241-luebeck-briefe/",
            forum_dir=self.temp_dir,
            thread_title="Lübeck Briefe 1865",
        )

        self.assertIsNotNone(result)
        self.assertTrue(os.path.isfile(result))
        self.assertTrue(result.endswith("Luebeck-Briefe-1865.html"))
        # Check parent folder is html
        self.assertEqual(os.path.basename(os.path.dirname(result)), "html")

        # Verify content
        with open(result, "r", encoding="utf-8") as f:
            saved_content = f.read()
        self.assertIn("Lübeck Briefe 1865", saved_content)
        self.assertIn('id="scraper-print-stylesheet"', saved_content)

    @patch("philaforum.scraper.fetch_url")
    @patch("philaforum.scraper.scrape_thread")
    def test_scrape_board_with_resume(self, mock_scrape_thread, mock_fetch_url):
        board_html = """
        <ul class="tabularList">
            <li class="tabularListRow">
                <h3 class="wbbTopicLink"><a href="https://philaforum.com/forum/thread/1-t1/">Thread 1</a></h3>
            </li>
            <li class="tabularListRow">
                <h3 class="wbbTopicLink"><a href="https://philaforum.com/forum/thread/2-t2/">Thread 2</a></h3>
            </li>
        </ul>
        """
        mock_fetch_url.return_value = board_html
        def mock_thread_impl(thread_url, forum_dir, thread_title, **kwargs):
            slug = sanitize_title_slug(thread_title)
            path = os.path.join(forum_dir, "html", f"{slug}.html")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("<html><body>dummy</body></html>")
            return path

        mock_scrape_thread.side_effect = mock_thread_impl

        scraped = scrape_board(
            board_url="https://philaforum.com/forum/board/241-l%C3%BCbeck/",
            output_dir=self.temp_dir,
            delay=0,
        )
        self.assertEqual(len(scraped), 2)

        # Verify boards.json was written (Thread 1 is newest, so with default from_last_page=True it is recorded last)
        boards_json_path = os.path.join(self.temp_dir, "boards.json")
        self.assertTrue(os.path.isfile(boards_json_path))
        reg = load_boards_registry(self.temp_dir)
        self.assertIn("Luebeck", reg)
        self.assertEqual(reg["Luebeck"]["last_thread_title"], "Thread 1")
        self.assertEqual(reg["Luebeck"]["last_html"], "Thread-1.html")
        threads_map = reg["Luebeck"]["threads"]
        self.assertEqual(len(threads_map), 1)
        self.assertIn("https://philaforum.com/forum/thread/1-t1/", threads_map)
        self.assertEqual(threads_map["https://philaforum.com/forum/thread/1-t1/"]["status"], "done")
        self.assertNotIn("https://philaforum.com/forum/thread/2-t2/", threads_map)

        # Second run: verify progress counter and (Done) label for already processed threads
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            scraped_again = scrape_board(
                board_url="https://philaforum.com/forum/board/241-l%C3%BCbeck/",
                output_dir=self.temp_dir,
                delay=0,
            )
            output = fake_out.getvalue()

        self.assertEqual(len(scraped_again), 0)
        self.assertIn("[1/2] (Done) 'Thread 2' already processed.", output)
        self.assertIn("[2/2] (Done) 'Thread 1' already processed.", output)

    @patch("philaforum.scraper.scrape_board")
    def test_cli_build_url_and_cookie_file(self, mock_scrape_board):
        import sys
        from philaforum.scraper import main as scraper_main

        # 1. Test --build-url alias with --cookie-file (default from_last_page=True)
        cookie_path = os.path.join(self.temp_dir, "my_cookies.txt")
        with open(cookie_path, "w", encoding="utf-8") as f:
            f.write("session=secret123")

        test_argv = [
            "scraper.py",
            "--build-url", "https://philaforum.com/forum/board/241-l%C3%BCbeck/",
            "--cookie-file", cookie_path,
            "--output-dir", self.temp_dir,
        ]
        with patch.object(sys, "argv", test_argv):
            scraper_main()

        mock_scrape_board.assert_called_with(
            board_url="https://philaforum.com/forum/board/241-l%C3%BCbeck/",
            output_dir=self.temp_dir,
            delay=1.0,
            limit=None,
            first_page_only=False,
            max_pages=None,
            force=False,
            cookie=None,
            cookie_file=cookie_path,
            page=None,
            from_last_page=True,
        )

        # 2. Test --page and --from-first-page CLI flags
        test_argv_page = [
            "scraper.py",
            "--build-url", "https://philaforum.com/forum/board/241-l%C3%BCbeck/",
            "--page", "3",
            "--from-first-page",
        ]
        with patch.object(sys, "argv", test_argv_page):
            scraper_main()

        mock_scrape_board.assert_called_with(
            board_url="https://philaforum.com/forum/board/241-l%C3%BCbeck/",
            output_dir=None,
            delay=1.0,
            limit=None,
            first_page_only=False,
            max_pages=None,
            force=False,
            cookie=None,
            cookie_file=None,
            page=3,
            from_last_page=False,
        )

        # 3. Test missing build-url / board-url causes SystemExit
        with patch.object(sys, "argv", ["scraper.py"]):
            with self.assertRaises(SystemExit):
                scraper_main()

    @patch("philaforum.scraper.fetch_url")
    @patch("philaforum.scraper.scrape_thread")
    def test_scrape_board_with_page_filter(self, mock_scrape_thread, mock_fetch_url):
        page2_html = """
        <ul class="tabularList">
            <li class="tabularListRow">
                <h3 class="wbbTopicLink"><a href="https://philaforum.com/forum/thread/20-t20/">Thread 20 (Page 2)</a></h3>
            </li>
        </ul>
        """
        mock_fetch_url.return_value = page2_html
        mock_scrape_thread.return_value = os.path.join(self.temp_dir, "html", "Thread-20.html")

        scraped = scrape_board(
            board_url="https://philaforum.com/forum/board/241-l%C3%BCbeck/",
            output_dir=self.temp_dir,
            delay=0,
            page=2,
        )

        self.assertEqual(len(scraped), 1)
        # Check fetch_url was called with pageNo=2
        mock_fetch_url.assert_called_with("https://philaforum.com/forum/board/241-l%C3%BCbeck/?pageNo=2")
        mock_scrape_thread.assert_called_once()
        self.assertEqual(mock_scrape_thread.call_args[1]["thread_title"], "Thread 20 (Page 2)")

    @patch("philaforum.scraper.fetch_url")
    @patch("philaforum.scraper.scrape_thread")
    def test_scrape_board_with_from_last_page(self, mock_scrape_thread, mock_fetch_url):
        page1_html = """
        <woltlab-core-pagination count="2"></woltlab-core-pagination>
        <ul class="tabularList">
            <li class="tabularListRow">
                <h3 class="wbbTopicLink"><a href="https://philaforum.com/forum/thread/1-t1/">Thread 1 (Newer)</a></h3>
            </li>
        </ul>
        """
        page2_html = """
        <ul class="tabularList">
            <li class="tabularListRow">
                <h3 class="wbbTopicLink"><a href="https://philaforum.com/forum/thread/2-t2/">Thread 2 (Older)</a></h3>
            </li>
            <li class="tabularListRow">
                <h3 class="wbbTopicLink"><a href="https://philaforum.com/forum/thread/3-t3/">Thread 3 (Oldest)</a></h3>
            </li>
        </ul>
        """

        def fetch_side_effect(url):
            if "pageNo=2" in url:
                return page2_html
            return page1_html

        mock_fetch_url.side_effect = fetch_side_effect
        mock_scrape_thread.side_effect = [
            os.path.join(self.temp_dir, "html", "Thread-3.html"),
            os.path.join(self.temp_dir, "html", "Thread-2.html"),
            os.path.join(self.temp_dir, "html", "Thread-1.html"),
        ]

        scraped = scrape_board(
            board_url="https://philaforum.com/forum/board/241-l%C3%BCbeck/",
            output_dir=self.temp_dir,
            delay=0,
            from_last_page=True,
        )

        self.assertEqual(len(scraped), 3)
        # Verify call order: Page 2 threads reversed (Thread 3, then Thread 2), then Page 1 (Thread 1)
        calls = [c[1]["thread_title"] for c in mock_scrape_thread.call_args_list]
        self.assertEqual(calls, ["Thread 3 (Oldest)", "Thread 2 (Older)", "Thread 1 (Newer)"])

    def test_prune_unwanted_html_elements(self):
        sample_html = """
        <header class="contentHeader">
            <nav class="breadcrumbs">
                <ul><li><a href="/forum/">Forum</a></li><li><a href="/forum/board/241/">Lübeck</a></li></ul>
            </nav>
            <h1 class="contentTitle">Lübeck Postgeschichte</h1>
        </header>
        <ul class="messageList">
            <li class="message">
                <div class="messageText">
                    <p>Hier ist ein Beleg. <img src="https://philaforum.com/images/smilies/emojione/26a0.png" class="smiley" alt=":warning:"> Danke!</p>
                    <p><a href="https://philaforum.com/images/smilies/emojione/1f600.png"><img src="https://philaforum.com/images/smilies/emojione/1f600.png" class="smiley"></a> Noch eins.</p>
                </div>
            </li>
            <li class="messageFooterNote lastModifiedLogEntry">Geändert von Admin (Gestern, 12:00)</li>
            <li class="lastModofiedLogEntry">Tippfehler behoben</li>
            <li class="messageQuickReply">
                <form action="/reply"><textarea name="text"></textarea></form>
            </li>
            <li id="messageQuickReply" class="jsOnly">
                <div class="messageQuickReplyContent"><textarea>QuickReplyID</textarea></div>
            </li>
        </ul>
        <div class="pageFooterStickyNotice">Bitte stimmen Sie den Cookies zu.</div>
        <div id="follow" class="jsFollowButton"><a href="/follow">Thema abonnieren</a></div>
        <div class="boxesFooterBoxes"><div class="box">Footer Werbung & Links</div></div>
        <div id="boxesFooterBoxes"><p>Alte Footerbox</p></div>
        <div id="wcf13" class="dialogContainer">
            <div class="dialog">
                <header>Dialog Header</header>
                <div class="dialogContent">Content</div>
                <footer class="dialogFooter"><button>Submit</button></footer>
            </div>
        </div>
        <article>
            <div class="messageContent">
                <footer class="messageFooter">
                    <div class="messageSignature"><p>Gruss, Tester</p></div>
                    <div class="messageFooterGroup">
                        <ul class="messageFooterButtons">
                            <li><a href="#" title="Zitieren">Zitieren</a></li>
                            <li><a href="#" title="Reagieren">Reagieren</a></li>
                        </ul>
                    </div>
                </footer>
            </div>
        </article>
        <div class="contentHeaderIcon">
            <img src="https://philaforum.com/images/avatars/7e/1099-7ed77bf81f9c833a318a89b35b91f14c869d7dc9.jpg" alt="" class="userAvatarImage" loading="lazy">
        </div>
        <div class="userAvatar">
            <span aria-hidden="true" tabindex="-1"><img src="https://philaforum.com/images/avatars/7e/1099-7ed77bf81f9c833a318a89b35b91f14c869d7dc9.jpg" alt="" class="userAvatarImage" loading="lazy"></span>
        </div>
        <div class="box32 messageHeaderWrapper">
            <span aria-hidden="true" tabindex="-1"><img src="https://philaforum.com/images/avatars/ce/1013-ce87f62b9124385fd13851f286019213c5c7174d.jpg" alt="" class="userAvatarImage" loading="lazy"></span>
        </div>
        <p><a href="https://philaforum.com/images/avatars/de/1272.jpg"><img src="https://philaforum.com/images/avatars/de/1272.jpg"></a></p>
        <img src="https://philaforum.com/images/avatars/standalone.jpg">
        """

        cleaned = prune_unwanted_html_elements(sample_html)

        # 1. lastModifiedLogEntry & lastModofiedLogEntry
        self.assertNotIn("lastModifiedLogEntry", cleaned)
        self.assertNotIn("lastModofiedLogEntry", cleaned)
        self.assertNotIn("Geändert von Admin", cleaned)
        self.assertNotIn("Tippfehler behoben", cleaned)

        # 2. messageQuickReply
        self.assertNotIn("messageQuickReply", cleaned)
        self.assertNotIn('<form action="/reply">', cleaned)
        self.assertNotIn("QuickReplyID", cleaned)

        # 3. boxesFooterBoxes
        self.assertNotIn("boxesFooterBoxes", cleaned)
        self.assertNotIn("Footer Werbung & Links", cleaned)
        self.assertNotIn("Alte Footerbox", cleaned)

        # 4. pageFooterStickyNotice
        self.assertNotIn("pageFooterStickyNotice", cleaned)
        self.assertNotIn("Bitte stimmen Sie den Cookies zu.", cleaned)

        # 5. #follow
        self.assertNotIn('id="follow"', cleaned)
        self.assertNotIn("Thema abonnieren", cleaned)

        # 6. #content > header > nav removed, title kept
        self.assertNotIn("<nav", cleaned)
        self.assertNotIn("breadcrumbs", cleaned)
        self.assertIn('<h1 class="contentTitle">Lübeck Postgeschichte</h1>', cleaned)

        # 7. smilies/emojione images and anchors removed
        self.assertNotIn("smilies/emojione", cleaned)
        self.assertNotIn("26a0.png", cleaned)
        self.assertNotIn("1f600.png", cleaned)

        # 8. #wcf13 > div > footer removed
        self.assertNotIn("Submit", cleaned)
        self.assertIn("Dialog Header", cleaned)

        # 9. <div class="messageFooterGroup"> removed (article > div > footer > div.messageFooterGroup)
        self.assertNotIn("messageFooterGroup", cleaned)
        self.assertNotIn("Zitieren", cleaned)
        self.assertNotIn("Reagieren", cleaned)
        self.assertIn("Gruss, Tester", cleaned)

        # 10. Avatar images and containers removed
        self.assertNotIn("userAvatar", cleaned)
        self.assertNotIn("contentHeaderIcon", cleaned)
        self.assertNotIn("images/avatars", cleaned)
        self.assertNotIn("1099-7ed77bf81f9c833a318a89b35b91f14c869d7dc9.jpg", cleaned)
        self.assertNotIn("1013-ce87f62b9124385fd13851f286019213c5c7174d.jpg", cleaned)

        # Regular post text preserved
        self.assertIn("Hier ist ein Beleg.", cleaned)
        self.assertIn("Danke!", cleaned)
        self.assertIn("Noch eins.", cleaned)

        # 10. Test explicit #content > header > nav without contentHeader class
        html_content_nav = '<div id="content"><header><nav class="crumbs">NavText</nav><h1 class="contentTitle">Header in Content</h1></header></div>'
        cleaned_content_nav = prune_unwanted_html_elements(html_content_nav)
        self.assertNotIn("NavText", cleaned_content_nav)
        self.assertNotIn("<nav", cleaned_content_nav)
        self.assertIn('<h1 class="contentTitle">Header in Content</h1>', cleaned_content_nav)

    def test_remove_wcf13_footer_variants(self):
        # Case 1: Dialog with header, content, and footer inside #wcf13 > div > footer
        html1 = """
        <div id="wcf13" class="dialogContainer">
            <div class="dialog">
                <header>Dialog Header</header>
                <div class="dialogBody">Dialog Body Text</div>
                <footer class="dialogFooter"><button>Close</button></footer>
            </div>
        </div>
        """
        out1 = remove_wcf13_footer(html1)
        self.assertNotIn("<footer", out1)
        self.assertNotIn("Close", out1)
        self.assertIn("Dialog Header", out1)
        self.assertIn("Dialog Body Text", out1)

        # Case 2: #wcf13 containing only div and footer -> completely pruned
        html2 = """
        <div id="wcf13">
            <div>
                <footer>Only footer inside wcf13</footer>
            </div>
        </div>
        """
        out2 = remove_wcf13_footer(html2)
        self.assertNotIn("wcf13", out2)
        self.assertNotIn("<footer", out2)
        self.assertNotIn("Only footer inside wcf13", out2)

        # Case 3: Direct footer element with id="wcf13"
        html3 = '<footer id="wcf13"><p>Direct Footer</p></footer>'
        out3 = remove_wcf13_footer(html3)
        self.assertNotIn("wcf13", out3)
        self.assertNotIn("Direct Footer", out3)

    def test_sanitize_thread_html_prunes_unwanted_elements(self):
        full_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Test Thread</title></head>
        <body id="tpl_wbb_thread">
            <header class="contentHeader">
                <nav class="breadcrumbs"><span>Breadcrumb Path</span></nav>
                <h1 class="contentTitle">Titel 1860</h1>
            </header>
            <div id="main">
                <ul class="messageList">
                    <li class="message">
                        <div class="messageText">
                            <p>Text mit Smiley <img src="/images/smilies/emojione/26a0.png"></p>
                        </div>
                    </li>
                    <li class="lastModifiedLogEntry">Edit log</li>
                    <li class="messageQuickReply">Schnellantwort</li>
                </ul>
            </div>
            <div id="follow">Abo</div>
            <div class="pageFooterStickyNotice">Sticky</div>
            <div class="boxesFooterBoxes">Unwanted Footer Content</div>
            <div id="wcf13"><div><footer>WCF13 Footer Text</footer></div></div>
            <article>
                <div class="messageContent">
                    <footer class="messageFooter">
                        <div class="messageFooterGroup"><button>Footer Buttons</button></div>
                    </footer>
                </div>
            </article>
            <div class="userAvatar">
                <span aria-hidden="true" tabindex="-1"><img src="https://philaforum.com/images/avatars/7e/1099.jpg" class="userAvatarImage"></span>
            </div>
            <div class="contentHeaderIcon">
                <img src="https://philaforum.com/images/avatars/7e/1099.jpg" class="userAvatarImage">
            </div>
        </body>
        </html>
        """
        sanitized = sanitize_thread_html(full_html)
        self.assertNotIn("<nav", sanitized)
        self.assertNotIn("Breadcrumb Path", sanitized)
        self.assertNotIn('<li class="lastModifiedLogEntry"', sanitized)
        self.assertNotIn("Edit log", sanitized)
        self.assertNotIn('<li class="messageQuickReply"', sanitized)
        self.assertNotIn("Schnellantwort", sanitized)
        self.assertNotIn('id="follow"', sanitized)
        self.assertNotIn("Abo", sanitized)
        self.assertNotIn("pageFooterStickyNotice", sanitized)
        self.assertNotIn("Sticky", sanitized)
        self.assertNotIn("boxesFooterBoxes", sanitized)
        self.assertNotIn("Unwanted Footer Content", sanitized)
        self.assertNotIn("smilies/emojione", sanitized)
        self.assertNotIn("WCF13 Footer Text", sanitized)
        self.assertNotIn('<div class="messageFooterGroup"', sanitized)
        self.assertNotIn("Footer Buttons", sanitized)
        self.assertNotIn('src="https://philaforum.com/images/avatars/', sanitized)
        self.assertNotIn('<div class="userAvatar"', sanitized)
        self.assertNotIn('<div class="contentHeaderIcon"', sanitized)
        self.assertIn('<h1 class="contentTitle">Titel 1860</h1>', sanitized)
        self.assertIn("Text mit Smiley", sanitized)

    @patch("urllib.request.urlopen")
    def test_avatar_images_ignored_and_not_downloaded(self, mock_urlopen):
        # 1. fetch_and_save_image returns (None, None) and makes no network call
        avatar_url = "https://philaforum.com/images/avatars/7e/1099-avatar.jpg"
        src, href = fetch_and_save_image(avatar_url, images_dir=self.temp_dir)
        self.assertIsNone(src)
        self.assertIsNone(href)
        mock_urlopen.assert_not_called()

        # 2. data: URIs are also ignored without network call
        data_url = "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4="
        src2, href2 = fetch_and_save_image(data_url, images_dir=self.temp_dir)
        self.assertIsNone(src2)
        self.assertIsNone(href2)
        mock_urlopen.assert_not_called()

        # 3. fetch_url returns empty string for avatar URLs without network call
        content = fetch_url(avatar_url)
        self.assertEqual(content, "")
        mock_urlopen.assert_not_called()

        # 4. embed_and_link_images strips avatar img tags completely
        html = (
            '<div>'
            '<a href="https://philaforum.com/images/avatars/de/1272.jpg">'
            '<img src="https://philaforum.com/images/avatars/de/1272.jpg" class="userAvatarImage">'
            '</a>'
            '<img src="https://philaforum.com/images/avatars/test.jpg">'
            '<span>Post Content</span>'
            '</div>'
        )
        res = embed_and_link_images(html, images_dir=self.temp_dir)
        self.assertNotIn("images/avatars", res)
        self.assertNotIn("<img", res)
        self.assertNotIn("<a", res)
        self.assertIn("Post Content", res)

    @patch("urllib.request.urlopen")
    def test_fetch_and_save_image_skips_when_exists_in_images_dir(self, mock_urlopen):
        from philaforum.scraper import _IMAGE_CACHE
        _IMAGE_CACHE.clear()

        images_dir = os.path.join(self.temp_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        img_file = os.path.join(images_dir, "999-myimage.jpg")
        with open(img_file, "wb") as f:
            f.write(b"dummy-image-bytes")

        # 1. Direct name match skips network request
        src, href = fetch_and_save_image(
            "https://philaforum.com/attachment/999-myimage.jpg",
            images_dir=images_dir,
            image_link_prefix="../images/",
        )
        mock_urlopen.assert_not_called()
        self.assertEqual(src, "../images/999-myimage.jpg")
        self.assertEqual(href, "../images/999-myimage.jpg")

    @patch("urllib.request.urlopen")
    def test_fetch_and_save_image_skips_by_attachment_id_prefix(self, mock_urlopen):
        from philaforum.scraper import _IMAGE_CACHE
        _IMAGE_CACHE.clear()

        images_dir = os.path.join(self.temp_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        # Image saved previously under detailed name
        saved_file = os.path.join(images_dir, "173480-img012-jpg.jpg")
        with open(saved_file, "wb") as f:
            f.write(b"dummy-image-bytes")

        # Request using attachment ID only with thumbnail param
        src, href = fetch_and_save_image(
            "https://philaforum.com/forum/attachment/173480/?thumbnail=1",
            images_dir=images_dir,
            image_link_prefix="../images/",
        )
        mock_urlopen.assert_not_called()
        self.assertEqual(src, "../images/173480-img012-jpg.jpg")
        self.assertEqual(href, "../images/173480-img012-jpg.jpg")

    @patch("urllib.request.urlopen")
    def test_fetch_and_save_image_skips_by_alternate_extension(self, mock_urlopen):
        from philaforum.scraper import _IMAGE_CACHE
        _IMAGE_CACHE.clear()

        images_dir = os.path.join(self.temp_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        # Image saved as .png on disk
        png_file = os.path.join(images_dir, "555-stamp.png")
        with open(png_file, "wb") as f:
            f.write(b"dummy-png-bytes")

        # Request without extension in URL (defaults to .jpg)
        src, href = fetch_and_save_image(
            "https://philaforum.com/attachment/555-stamp/",
            images_dir=images_dir,
            image_link_prefix="../images/",
        )
        mock_urlopen.assert_not_called()
        self.assertEqual(src, "../images/555-stamp.png")
        self.assertEqual(href, "../images/555-stamp.png")

    @patch("urllib.request.urlopen")
    def test_embed_and_link_images_skips_download_when_image_already_in_images_dir(self, mock_urlopen):
        from philaforum.scraper import _IMAGE_CACHE
        _IMAGE_CACHE.clear()

        images_dir = os.path.join(self.temp_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        img_path = os.path.join(images_dir, "1234-briefmarke.jpg")
        with open(img_path, "wb") as f:
            f.write(b"stamp-image")

        html = (
            '<div>'
            '<a href="https://philaforum.com/attachment/1234-briefmarke.jpg">'
            '<img src="https://philaforum.com/attachment/1234-briefmarke.jpg?thumbnail=1">'
            '</a>'
            '</div>'
        )

        res = embed_and_link_images(html, images_dir=images_dir, image_link_prefix="../images/")
        mock_urlopen.assert_not_called()
        self.assertIn('src="../images/1234-briefmarke.jpg"', res)
        self.assertIn('href="../images/1234-briefmarke.jpg"', res)

    def test_remove_tag_blocks_linear_and_nested(self):
        # 1. Nested tags
        html_nested = '<main><div class="removeMe"><div class="inner">Inner text</div>More text</div><p>Keep Me</p></main>'
        cleaned = remove_tag_blocks(html_nested, r'<div\b[^>]*class="[^"]*removeMe[^"]*"[^>]*>', 'div')
        self.assertNotIn("removeMe", cleaned)
        self.assertNotIn("Inner text", cleaned)
        self.assertNotIn("More text", cleaned)
        self.assertIn("<p>Keep Me</p>", cleaned)

        # 2. Multiple sequential blocks in large repetitive text
        blocks = "".join([f'<div class="ad">Ad #{i} <span>Sponsored</span></div><p>Paragraph #{i}</p>' for i in range(100)])
        cleaned_blocks = remove_tag_blocks(blocks, r'<div\b[^>]*class="[^"]*ad[^"]*"[^>]*>', 'div')
        self.assertNotIn("Sponsored", cleaned_blocks)
        self.assertNotIn('class="ad"', cleaned_blocks)
        self.assertIn("Paragraph #0", cleaned_blocks)
        self.assertIn("Paragraph #99", cleaned_blocks)

        # 3. Empty or no match
        self.assertEqual(remove_tag_blocks("", r'<div\b', 'div'), "")
        self.assertEqual(remove_tag_blocks("<p>Hello</p>", r'<div\b', 'div'), "<p>Hello</p>")

    @patch("philaforum.scraper.fetch_url")
    def test_scrape_thread_progress_messages(self, mock_fetch_url):
        mock_fetch_url.return_value = """
        <html><head><title>Title</title></head><body>
        <div class="contentHeader"><h1 class="contentTitle">Multi-Page Thread</h1></div>
        <ul class="messageList"><li class="message"><div class="messageText">Text</div></li></ul>
        </body></html>
        """
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            res = scrape_thread(
                thread_url="https://philaforum.com/forum/thread/999-test/?pageNo=1",
                forum_dir=self.temp_dir,
                first_page_only=True,
            )
            out = fake_out.getvalue()
        self.assertIsNotNone(res)
        self.assertIn("Combining posts from 1 page(s)...", out)
        self.assertIn("Sanitizing combined thread HTML", out)
        self.assertIn("[SUCCESS] Saved", out)



class TestPhilaforumTranslatorPureHtml(unittest.TestCase):
    """Test suite for philaforum.util.translate functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.html_dir = os.path.join(self.temp_dir, "html")
        self.images_dir = os.path.join(self.temp_dir, "images")
        os.makedirs(self.html_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clean_translated_text(self):
        raw1 = "**Direct Translation:** This is a rare postmark from Lübeck."
        self.assertEqual(clean_translated_text(raw1, "orig"), "This is a rare postmark from Lübeck.")

        raw2 = 'Here is the direct translation: "Auction item #42 sold for 500 Euros."'
        self.assertEqual(clean_translated_text(raw2, "orig"), "Auction item #42 sold for 500 Euros.")

        raw3 = "Dear Carolinus, I am ready to translate your text."
        self.assertEqual(clean_translated_text(raw3, "orig"), "orig")

    def test_update_image_links_to_root(self):
        html_input = """
        <html>
        <head><base href="https://philaforum.com/"></head>
        <body>
        <p><img src="../images/100-marke.jpg"></p>
        <p><a href="../images/100-marke.jpg">Click</a></p>
        <p><img src="../image/old-folder.jpg"></p>
        </body>
        </html>
        """
        updated = update_image_links_to_root(html_input, images_dirname="images")
        self.assertNotIn("<base", updated.lower())
        self.assertIn('src="images/100-marke.jpg"', updated)
        self.assertIn('href="images/100-marke.jpg"', updated)
        self.assertIn('src="images/old-folder.jpg"', updated)
        self.assertNotIn("../images/", updated)
        self.assertNotIn("../image/", updated)

    @patch("util.translation.query_ollama_translation")
    def test_translate_post_text_preserves_images(self, mock_ollama):
        mock_ollama.side_effect = lambda text, **kwargs: f"EN: {text}"

        post_body = """
        <p>Hallo Sammlerfreunde,</p>
        <div class="attachmentImagePreview">
            <a href="../images/100-luebeck.jpg"><img src="../images/100-luebeck.jpg"></a>
        </div>
        <blockquote>Altes Zitat aus 1865</blockquote>
        <p>Sehr schöner Beleg.</p>
        """
        translated = translate_post_text(
            post_body,
            source_lang="de",
            target_lang="en",
            model="codegemma:7b",
            ollama_url="http://localhost:11434",
        )

        # Image preview tag intact
        self.assertIn('class="attachmentImagePreview"', translated)
        self.assertIn('src="../images/100-luebeck.jpg"', translated)
        # Blockquote translated
        self.assertIn("<blockquote><p>EN: Altes Zitat aus 1865</p></blockquote>", translated)
        # Paragraphs translated
        self.assertIn("<p>EN: Hallo Sammlerfreunde,</p>", translated)
        self.assertIn("<p>EN: Sehr schöner Beleg.</p>", translated)

    @patch("util.translation.query_ollama_translation")
    def test_translate_thread_html(self, mock_ollama):
        mock_ollama.side_effect = lambda text, **kwargs: f"EN: {text}"

        german_html = """
        <html>
        <head><title>Lübeck Postgeschichte</title></head>
        <body>
        <div class="contentHeader"><h1 class="contentTitle">Lübeck Postgeschichte</h1></div>
        <ul class="messageList">
            <li class="message">
                <div class="messageContent">
                    <div class="messageText">
                        <p>Ein seltener Brief aus 1860.</p>
                        <p><a href="../images/brief.jpg"><img src="../images/brief.jpg"></a></p>
                    </div>
                </div>
            </li>
        </ul>
        </body>
        </html>
        """
        translated_html, trans_title = translate_thread_html(
            german_html,
            source_lang="de",
            target_lang="en",
            model="codegemma:7b",
            ollama_url="http://localhost:11434",
            images_dirname="images",
        )

        self.assertEqual(trans_title, "EN: Lübeck Postgeschichte")
        self.assertIn("<title>EN: Lübeck Postgeschichte (EN)</title>", translated_html)
        self.assertIn('class="contentTitle">EN: Lübeck Postgeschichte</h1>', translated_html)
        self.assertIn("<p>EN: Ein seltener Brief aus 1860.</p>", translated_html)
        # Image links updated to root images/
        self.assertIn('href="images/brief.jpg"', translated_html)
        self.assertIn('src="images/brief.jpg"', translated_html)
        self.assertNotIn("../images/", translated_html)

    def test_translation_registry_io(self):
        reg_path = os.path.join(self.temp_dir, "translate.json")
        record_translation_in_registry(
            registry_path=reg_path,
            source_filename="html/Luebeck-1.html",
            translated_filename="Luebeck-1.html",
            translated_title="Lübeck Postal History 1",
            model="codegemma:7b",
        )

        loaded = load_translation_registry(reg_path)
        self.assertEqual(loaded["last_translated_file"], "Luebeck-1.html")
        self.assertEqual(len(loaded["translations"]), 1)
        self.assertIn("Luebeck-1.html", loaded["translations"])
        self.assertEqual(loaded["translations"]["Luebeck-1.html"]["status"], "completed")
        self.assertEqual(loaded["translations"]["Luebeck-1.html"]["translated_title"], "Lübeck Postal History 1")

        # Record a second translation: verify only the last one is stored in translations
        record_translation_in_registry(
            registry_path=reg_path,
            source_filename="html/Luebeck-2.html",
            translated_filename="Luebeck-2.html",
            translated_title="Lübeck Postal History 2",
            model="codegemma:7b",
        )

        loaded2 = load_translation_registry(reg_path)
        self.assertEqual(loaded2["last_translated_file"], "Luebeck-2.html")
        self.assertEqual(len(loaded2["translations"]), 1)
        self.assertIn("Luebeck-2.html", loaded2["translations"])
        self.assertNotIn("Luebeck-1.html", loaded2["translations"])
        self.assertEqual(loaded2["translations"]["Luebeck-2.html"]["translated_title"], "Lübeck Postal History 2")

    def test_translation_registry_fallback_and_sync(self):
        # 1. Verify default resolution when neither exists
        res_default = resolve_registry_path(self.temp_dir)
        self.assertEqual(os.path.basename(res_default), "translate.json")

        # 2. When only translation.json exists, resolve and load from it
        legacy_path = os.path.join(self.temp_dir, "translation.json")
        with open(legacy_path, "w", encoding="utf-8") as f:
            json.dump({
                "translations": {
                    "Old.html": {"status": "completed", "source_file": "Old.html", "translated_file": "Old.html"}
                },
                "last_translated_file": "Old.html"
            }, f)

        res_legacy = resolve_registry_path(self.temp_dir)
        self.assertEqual(res_legacy, legacy_path)

        # Loading from translate.json path when only translation.json exists transparently falls back
        loaded = load_translation_registry(os.path.join(self.temp_dir, "translate.json"))
        self.assertEqual(loaded["last_translated_file"], "Old.html")
        self.assertIn("Old.html", loaded["translations"])

        # 3. Saving to translate.json synchronizes with existing translation.json
        record_translation_in_registry(
            registry_path=os.path.join(self.temp_dir, "translate.json"),
            source_filename="html/New.html",
            translated_filename="New.html",
            translated_title="New Title",
        )

        with open(legacy_path, "r", encoding="utf-8") as f:
            legacy_data = json.load(f)
        self.assertEqual(legacy_data["last_translated_file"], "New.html")
        self.assertEqual(len(legacy_data["translations"]), 1)
        self.assertIn("New.html", legacy_data["translations"])

    @patch("util.translation.query_ollama_translation")
    def test_translate_single_html_file(self, mock_ollama):
        mock_ollama.side_effect = lambda text, **kwargs: f"EN: {text}"

        source_file = os.path.join(self.html_dir, "Luebeck.html")
        with open(source_file, "w", encoding="utf-8") as f:
            f.write("""
            <html><head><title>Deutscher Titel</title></head><body>
            <div class="contentHeader"><h1 class="contentTitle">Deutscher Titel</h1></div>
            <div class="messageText"><p>Deutscher Text.</p><img src="../images/foto.jpg"></div>
            </body></html>
            """)

        target_file = os.path.join(self.temp_dir, "Luebeck.html")
        reg_file = os.path.join(self.temp_dir, "translate.json")

        result = translate_single_html_file(
            source_html_path=source_file,
            target_html_path=target_file,
            registry_path=reg_file,
        )

        self.assertIsNotNone(result)
        self.assertTrue(os.path.isfile(target_file))

        with open(target_file, "r", encoding="utf-8") as f:
            translated_content = f.read()

        self.assertIn("EN: Deutscher Titel", translated_content)
        self.assertIn("EN: Deutscher Text.", translated_content)
        self.assertIn('src="images/foto.jpg"', translated_content)

        # Check registry
        reg = load_translation_registry(reg_file)
        self.assertEqual(reg["last_translated_file"], "Luebeck.html")
        self.assertEqual(len(reg["translations"]), 1)
        self.assertIn("Luebeck.html", reg["translations"])

    @patch("util.translation.query_ollama_translation")
    def test_translate_forum_directory_batch_and_resume(self, mock_ollama):
        mock_ollama.side_effect = lambda text, **kwargs: f"EN: {text}"

        # Create two files in html/
        for name in ["01-Brief.html", "02-Stempel.html"]:
            with open(os.path.join(self.html_dir, name), "w", encoding="utf-8") as f:
                f.write(f"<html><head><title>{name}</title></head><body><div class='messageText'><p>{name}</p></div></body></html>")

        # First run: translate both files
        translated = translate_forum_directory(
            forum_dir=self.temp_dir,
            model="codegemma:7b",
        )
        self.assertEqual(len(translated), 2)
        self.assertTrue(os.path.isfile(os.path.join(self.temp_dir, "01-Brief.html")))
        self.assertTrue(os.path.isfile(os.path.join(self.temp_dir, "02-Stempel.html")))

        # Check translate.json - only the last file should be in translations
        reg_path = os.path.join(self.temp_dir, "translate.json")
        reg = load_translation_registry(reg_path)
        self.assertEqual(reg["last_translated_file"], "02-Stempel.html")
        self.assertEqual(len(reg["translations"]), 1)
        self.assertIn("02-Stempel.html", reg["translations"])
        self.assertNotIn("01-Brief.html", reg["translations"])

        # Second run: without force, should skip both completed files on disk
        mock_ollama.reset_mock()
        translated_again = translate_forum_directory(
            forum_dir=self.temp_dir,
            force=False,
            resume=True,
        )
        self.assertEqual(len(translated_again), 0)
        self.assertEqual(mock_ollama.call_count, 0)


if __name__ == "__main__":
    unittest.main()
