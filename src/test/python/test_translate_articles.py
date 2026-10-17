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

"""Unit tests for src/main/python/scraper/translate-articles.py."""

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# Dynamically import translate-articles.py due to hyphen in filename
MODULE_PATH = Path(__file__).resolve().parents[2] / "main" / "python" / "scraper" / "translate-articles.py"
spec = importlib.util.spec_from_file_location("translate_articles", MODULE_PATH)
ta = importlib.util.module_from_spec(spec)
sys.modules["translate_articles"] = ta
spec.loader.exec_module(ta)


class TestTranslateArticles(unittest.TestCase):
    """Unit tests for translate-articles.py functions and CLI workflow."""

    def test_get_language_name(self):
        """Test ISO 639-1 code to full language name conversion."""
        self.assertEqual(ta.get_language_name("de"), "German")
        self.assertEqual(ta.get_language_name("DE"), "German")
        self.assertEqual(ta.get_language_name(" fr "), "French")
        self.assertEqual(ta.get_language_name("en"), "English")
        self.assertEqual(ta.get_language_name("es"), "Spanish")
        self.assertEqual(ta.get_language_name("it"), "Italian")
        self.assertEqual(ta.get_language_name("nl"), "Dutch")
        self.assertEqual(ta.get_language_name("xyz"), "Language (xyz)")

    @patch("urllib.request.urlopen")
    def test_check_ollama_available_success(self, mock_urlopen):
        """Test Ollama availability check when endpoint is reachable."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        self.assertTrue(ta.check_ollama_available("http://localhost:11434"))

    @patch("urllib.request.urlopen", side_effect=Exception("Connection refused"))
    def test_check_ollama_available_failure(self, mock_urlopen):
        """Test Ollama availability check when endpoint is unreachable."""
        self.assertFalse(ta.check_ollama_available("http://localhost:11434"))

    def test_parse_arguments_input_folder(self):
        """Test CLI parsing with --input-folder and defaults."""
        args = ta.parse_arguments(["--input-folder", "/path/to/pdfs"])
        self.assertEqual(args.input_folder, "/path/to/pdfs")
        self.assertIsNone(args.input_file)
        self.assertEqual(args.lang, "de")
        self.assertEqual(args.target_lang, "en")
        self.assertEqual(args.model, ta.DEFAULT_MODEL)
        self.assertFalse(args.force)
        self.assertFalse(args.save_text)

    def test_parse_arguments_camelcase_input_folder(self):
        """Test CLI parsing with camelCase --inputFolder."""
        args = ta.parse_arguments(["--inputFolder", "/path/to/pdfs"])
        self.assertEqual(args.input_folder, "/path/to/pdfs")

    def test_parse_arguments_input_file(self):
        """Test CLI parsing with --input-file and custom flags."""
        args = ta.parse_arguments([
            "--input-file", "/path/to/article.pdf",
            "--lang", "fr",
            "--target-lang", "en",
            "--model", "deepseek-coder-v2:16b",
            "--force",
            "--save-text",
            "--render-timeout", "450",
        ])
        self.assertEqual(args.input_file, "/path/to/article.pdf")
        self.assertIsNone(args.input_folder)
        self.assertEqual(args.lang, "fr")
        self.assertEqual(args.target_lang, "en")
        self.assertEqual(args.model, "deepseek-coder-v2:16b")
        self.assertTrue(args.force)
        self.assertTrue(args.save_text)
        self.assertEqual(args.render_timeout, 450)

    def test_parse_arguments_camelcase_input_file(self):
        """Test CLI parsing with camelCase --inputFile."""
        args = ta.parse_arguments(["--inputFile", "/path/to/article.pdf"])
        self.assertEqual(args.input_file, "/path/to/article.pdf")

    def test_parse_arguments_missing_required(self):
        """Test CLI parsing fails when neither --input-folder nor --input-file is given."""
        with patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit):
                ta.parse_arguments([])

    def test_update_image_links_for_subfolder(self):
        """Test converting image URLs from images/ to ../images/ for subfolder depth."""
        # 1. Standard relative src and href
        html_input = '<img src="images/stamp1.png"><a href=\'images/stamp2.jpg\'>Link</a>'
        expected = '<img src="../images/stamp1.png"><a href=\'../images/stamp2.jpg\'>Link</a>'
        self.assertEqual(ta.update_image_links_for_subfolder(html_input), expected)

        # 2. Leading ./images/ paths
        html_input = '<img src="./images/stamp.png">'
        expected = '<img src="../images/stamp.png">'
        self.assertEqual(ta.update_image_links_for_subfolder(html_input), expected)

        # 3. Absolute file:/// paths pointing into an images folder
        html_input = '<a href="file:///D:/workspace/output/images/entry.png">Image</a>'
        expected = '<a href="../images/entry.png">Image</a>'
        self.assertEqual(ta.update_image_links_for_subfolder(html_input), expected)

        # 4. External or non-image URLs should remain untouched
        html_input = '<img src="https://philaforum.com/images/logo.png"><a href="other/path.html">Other</a>'
        self.assertEqual(ta.update_image_links_for_subfolder(html_input), html_input)

        # 5. Strips <base href="..."> completely so headless Chrome does not redirect relative paths to remote site
        html_with_base = '<head><base href="https://philaforum.com/forum/thread/123/"><title>T</title></head><img src="images/test.jpg">'
        expected_no_base = '<head><title>T</title></head><img src="../images/test.jpg">'
        self.assertEqual(ta.update_image_links_for_subfolder(html_with_base), expected_no_base)

        # 6. Attachment URL mapping using images_dir
        with tempfile.TemporaryDirectory() as tmp_images:
            # Create a sample image file in tmp_images
            img_file = os.path.join(tmp_images, "244046-img321.jpg")
            with open(img_file, "wb") as f:
                f.write(b"fake image data")

            att_html = '<a href="https://philaforum.com/attachment/244046-img321-jpg/"><img src="https://philaforum.com/attachment/244046-img321-jpg/?thumbnail=1"></a>'
            mapped_html = ta.update_image_links_for_subfolder(att_html, images_dir=tmp_images)
            self.assertIn('href="../images/244046-img321.jpg"', mapped_html)
            self.assertIn('src="../images/244046-img321.jpg"', mapped_html)

    @patch("urllib.request.urlopen")
    def test_query_ollama_translation_success(self, mock_urlopen):
        """Test successful Ollama translation query."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "message": {"content": "Inverted center stamp description"}
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = ta.query_ollama_translation(
            text="Kopfstehendem Mittelstueck Beschreibung",
            source_lang="de",
            target_lang="en",
        )
        self.assertEqual(result, "Inverted center stamp description")

    @patch("urllib.request.urlopen")
    def test_query_ollama_translation_strips_quotes(self, mock_urlopen):
        """Test stripping outer quotes returned by the LLM."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "message": {"content": '"Translated with extra quotes"'}
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = ta.query_ollama_translation("Original", source_lang="de")
        self.assertEqual(result, "Translated with extra quotes")

    def test_clean_translated_text_strips_prompt_leak(self):
        """Test that leaked system prompt instructions are stripped from model output."""
        leak_input = (
            "You are an expert translator specializing in German to English translations with "
            "deep domain knowledge of philatelic (stamp collecting), postal history, and auction terminology.\n"
            "Key philatelic terminology guidelines: - 'kopfstehendes Mittelstück' -> 'inverted center' "
            "- 'Zähnung' -> 'perforation'\n"
            "Many greetings, carolinus"
        )
        cleaned = ta.clean_translated_text(leak_input, "Viele Grüße carolinus")
        self.assertEqual(cleaned, "Many greetings, carolinus")

    def test_clean_translated_text_strips_preamble_markers(self):
        """Test stripping **Direct Translation:** and similar preamble wrappers."""
        self.assertEqual(
            ta.clean_translated_text("**Direct Translation:** Plate flaw on stamp", "orig"),
            "Plate flaw on stamp",
        )
        self.assertEqual(
            ta.clean_translated_text("### Translation:\nInverted center cover", "orig"),
            "Inverted center cover",
        )
        self.assertEqual(
            ta.clean_translated_text("The provided text translates as follows: Rare postmark", "orig"),
            "Rare postmark",
        )

    def test_clean_translated_text_discards_conversational_refusal(self):
        """Test that conversational readiness echoes like 'Dear ..., I am ready to translate' are discarded."""
        refusal = "Dear Carolinus, I am ready to translate your text from German to English. Please provide the text."
        self.assertEqual(
            ta.clean_translated_text(refusal, "Original German text"),
            "Original German text",
        )

    def test_query_ollama_translation_empty_string(self):
        """Test that empty or whitespace strings return immediately without network call."""
        self.assertEqual(ta.query_ollama_translation(""), "")
        self.assertEqual(ta.query_ollama_translation("   "), "   ")

    @patch("urllib.request.urlopen", side_effect=Exception("Timeout"))
    def test_query_ollama_translation_fallback_on_error(self, mock_urlopen):
        """Test fallback to original text if Ollama connection fails."""
        original = "Original German text"
        result = ta.query_ollama_translation(original, source_lang="de", max_retries=1)
        self.assertEqual(result, original)

    def test_extract_thread_url_from_pdf(self):
        """Test extraction of forum thread URL from PDF URI annotations."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf_path = tf.name
            # Write synthetic PDF stream with /URI annotation
            tf.write(
                b"%PDF-1.4\n1 0 obj\n<< /Type /Annot /Subtype /Link /A << /S /URI "
                b"/URI (https://philaforum.com/forum/thread/5790-bayern-3-kreuzer-blau/?pageNo=2#post123) >> >>\n"
                b"endobj\n%%EOF"
            )

        try:
            url = ta.extract_thread_url_from_pdf(tf_path)
            self.assertEqual(url, "https://philaforum.com/forum/thread/5790-bayern-3-kreuzer-blau/")
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_extract_thread_url_from_pdf_octal_escaped(self):
        """Test extraction of forum thread URL with Chrome/Skia octal-escaped characters."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf_path = tf.name
            tf.write(
                b"%PDF-1.4\n1 0 obj\n<< /Type /Annot /Subtype /Link /A << /S /URI "
                b"/URI (https\\072\\057\\057philaforum\\056com\\057forum\\057thread\\05737787\\055adlerausgabe\\055michel\\055nr\\05544\\057) >> >>\n"
                b"endobj\n%%EOF"
            )

        try:
            url = ta.extract_thread_url_from_pdf(tf_path)
            self.assertEqual(url, "https://philaforum.com/forum/thread/37787-adlerausgabe-michel-nr-44/")
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_extract_thread_url_from_pdf_hex_encoded(self):
        """Test extraction of forum thread URL from hex-encoded /URI literal."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf_path = tf.name
            # Hex of "https://philaforum.com/forum/thread/100-test/"
            hex_str = "https://philaforum.com/forum/thread/100-test/".encode("utf-8").hex().encode("ascii")
            tf.write(
                b"%PDF-1.4\n1 0 obj\n<< /Type /Annot /Subtype /Link /A << /S /URI "
                b"/URI <" + hex_str + b"> >> >>\nendobj\n%%EOF"
            )

        try:
            url = ta.extract_thread_url_from_pdf(tf_path)
            self.assertEqual(url, "https://philaforum.com/forum/thread/100-test/")
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_extract_thread_url_from_pdf_missing(self):
        """Test extracting thread URL returns None if not present in PDF."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf_path = tf.name
            tf.write(b"%PDF-1.4\nPlain PDF without annotations\n%%EOF")

        try:
            url = ta.extract_thread_url_from_pdf(tf_path)
            self.assertIsNone(url)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_save_text_strips_style_blocks(self):
        """Test that HTML style and script blocks do not leak into text file output."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = os.path.join(tmp_dir, "source.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4\n")

            out_dir = os.path.join(tmp_dir, "en")
            os.makedirs(out_dir, exist_ok=True)

            with patch.object(ta, "extract_thread_url_from_pdf", return_value=None), \
                 patch.object(ta, "extract_text_from_pdf_fallback", return_value="Paragraph 1"), \
                 patch.object(ta, "query_ollama_translation", return_value="Translated text"), \
                 patch.object(ta, "render_html_to_pdf", return_value=True):

                ta.translate_single_pdf(
                    pdf_path=pdf_path,
                    output_dir=out_dir,
                    browser_path="dummy",
                    save_text=True,
                    force=True,
                )

                txt_path = os.path.join(out_dir, "text", "source.txt")
                self.assertTrue(os.path.isfile(txt_path))
                with open(txt_path, "r", encoding="utf-8") as f:
                    txt_content = f.read()
                self.assertNotIn("font-family", txt_content)
                self.assertNotIn("@media", txt_content)
                self.assertIn("=== Translated text ===", txt_content)

    @patch.object(ta, "query_ollama_translation")
    def test_translate_post_text_preserves_images(self, mock_trans):
        """Test that translate_post_text preserves embedded images, attachments, and translates text."""
        mock_trans.side_effect = lambda text, **kwargs: f"EN: {text}"

        post_html = (
            "<p>Hallo zusammen,</p>"
            '<div class="attachmentImagePreview"><img src="images/stamp.png" alt="Stamp"></div>'
            "<p>Hier ist die MiNr 97.</p>"
            '<a class="embeddedImageLink" href="images/large.png"><img src="images/small.png"></a>'
        )

        translated = ta.translate_post_text(
            inner_html=post_html,
            source_lang="de",
            target_lang="en",
            model="codegemma:7b",
            ollama_url="http://localhost:11434",
        )

        # Image containers must be intact
        self.assertIn('<div class="attachmentImagePreview"><img src="images/stamp.png" alt="Stamp"></div>', translated)
        self.assertIn('<a class="embeddedImageLink" href="images/large.png"><img src="images/small.png"></a>', translated)
        # Text must be translated
        self.assertIn("<p>EN: Hallo zusammen,</p>", translated)
        self.assertIn("<p>EN: Hier ist die MiNr 97.</p>", translated)

    @patch.object(ta, "query_ollama_translation")
    def test_translate_post_text_blockquote(self, mock_trans):
        """Test translation of blockquote citations."""
        mock_trans.side_effect = lambda text, **kwargs: f"EN: {text}"

        post_html = (
            '<blockquote><p>Zitat aus Michel-Katalog</p></blockquote>'
            '<p>Antwort zum Zitat.</p>'
        )

        translated = ta.translate_post_text(
            inner_html=post_html,
            source_lang="de",
            target_lang="en",
            model="codegemma:7b",
            ollama_url="http://localhost:11434",
        )

        self.assertIn("EN: Zitat aus Michel-Katalog", translated)
        self.assertIn("EN: Antwort zum Zitat.", translated)

    @patch.object(ta, "query_ollama_translation")
    def test_translate_thread_html(self, mock_trans):
        """Test translate_thread_html translates title, updates images, and translates post messages."""
        mock_trans.side_effect = lambda text, **kwargs: f"EN: {text}"

        html_doc = """<!DOCTYPE html>
<html>
<head><title>Originaler Titel</title></head>
<body>
<h1 class="contentTitle">Originaler Titel</h1>
<div class="messageText"><p>Deutscher Post Inhalt mit <img src="images/test.png"></p></div></div>
</body>
</html>"""

        translated_html, translated_title = ta.translate_thread_html(
            html_content=html_doc,
            source_lang="de",
            target_lang="en",
        )

        self.assertEqual(translated_title, "EN: Originaler Titel")
        self.assertIn("<title>EN: Originaler Titel (EN)</title>", translated_html)
        self.assertIn('<h1 class="contentTitle">EN: Originaler Titel</h1>', translated_html)
        # Image src should be rewritten to ../images/
        self.assertIn('<img src="../images/test.png">', translated_html)

    def test_translate_single_pdf_skip_existing(self):
        """Test skipping translation when target PDF exists and force=False."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = os.path.join(tmp_dir, "sample.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 sample content")

            out_dir = os.path.join(tmp_dir, "en")
            os.makedirs(out_dir, exist_ok=True)
            target_pdf = os.path.join(out_dir, "sample.pdf")
            with open(target_pdf, "wb") as f:
                f.write(b"%PDF-1.4 existing translated content")

            # Call translate_single_pdf with force=False
            res = ta.translate_single_pdf(
                pdf_path=pdf_path,
                output_dir=out_dir,
                browser_path="dummy_browser",
                force=False,
            )
            self.assertEqual(res, target_pdf)

    @patch.object(ta, "render_html_to_pdf", return_value=True)
    @patch.object(ta, "translate_thread_html")
    @patch.object(ta, "fetch_url", return_value="<html><head></head><body>Sample</body></html>")
    @patch.object(ta, "extract_thread_url_from_pdf", return_value="https://philaforum.com/forum/thread/123-title/")
    def test_translate_single_pdf_online_flow(self, mock_extract, mock_fetch, mock_trans_html, mock_render):
        """Test full translation workflow using extracted online thread URL."""
        mock_trans_html.return_value = ("<html>Translated</html>", "English Title")

        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = os.path.join(tmp_dir, "article.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 content")

            out_dir = os.path.join(tmp_dir, "en")
            os.makedirs(out_dir, exist_ok=True)

            res = ta.translate_single_pdf(
                pdf_path=pdf_path,
                output_dir=out_dir,
                browser_path="dummy_browser",
                force=True,
                save_text=True,
            )

            expected_pdf = os.path.join(out_dir, "article.pdf")
            expected_txt = os.path.join(out_dir, "text", "article.txt")

            self.assertEqual(res, expected_pdf)
            mock_render.assert_called_once()
            # Verify text file was written in en/text/ subfolder
            self.assertTrue(os.path.isdir(os.path.join(out_dir, "text")))
            self.assertTrue(os.path.isfile(expected_txt))
            with open(expected_txt, "r", encoding="utf-8") as tf:
                content = tf.read()
                self.assertIn("English Title", content)

    def test_ensure_image_scaling_styles_injected(self):
        """Verify that ensure_image_scaling_styles injects unconstraining CSS rules before </head>."""
        html_input = "<html><head><title>Test</title></head><body><p>Hello</p></body></html>"
        res = ta.ensure_image_scaling_styles(html_input)
        self.assertIn(".messageAttachmentList", res)
        self.assertIn(".messageAttachment", res)
        self.assertIn(".attachmentImagePreview", res)
        self.assertIn("max-height: 850px", res)
        self.assertIn("grid-template-columns: none !important", res)

    def test_ensure_image_scaling_styles_already_present(self):
        """Verify that ensure_image_scaling_styles is idempotent if styles are already included."""
        html_input = (
            "<html><head><style>"
            ".messageAttachmentList { display: block !important; }"
            ".attachmentImagePreview { width: 100% !important; }"
            "</style></head><body><p>Hello</p></body></html>"
        )
        res = ta.ensure_image_scaling_styles(html_input)
        self.assertEqual(res, html_input)

    @patch.object(ta, "render_html_to_pdf", return_value=True)
    @patch.object(ta, "translate_thread_html", return_value=("<html>Translated</html>", "Title"))
    @patch.object(ta, "fetch_url", return_value="<html><body>Thread</body></html>")
    @patch.object(ta, "extract_thread_url_from_pdf", return_value="https://philaforum.com/forum/thread/123-title/")
    @patch.object(ta, "sanitize_thread_html")
    def test_translate_single_pdf_locates_images_dir_in_parent_folder(
        self, mock_sanitize, mock_extract, mock_fetch, mock_trans, mock_render
    ):
        """Verify that translate_single_pdf resolves images_dir in the parent directory for language subfolders."""
        mock_sanitize.return_value = "<html>Sanitized</html>"
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Layout: tmp_dir/board/de/article.pdf and tmp_dir/board/images/
            board_dir = os.path.join(tmp_dir, "Bayern")
            de_dir = os.path.join(board_dir, "de")
            images_dir = os.path.join(board_dir, "images")
            en_dir = os.path.join(board_dir, "en")
            os.makedirs(de_dir, exist_ok=True)
            os.makedirs(images_dir, exist_ok=True)

            pdf_path = os.path.join(de_dir, "article.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 test")

            ta.translate_single_pdf(
                pdf_path=pdf_path,
                output_dir=en_dir,
                browser_path="dummy_browser",
                force=True,
            )

            # mock_sanitize should have been called with images_dir=images_dir
            mock_sanitize.assert_called_once()
            _, kwargs = mock_sanitize.call_args
            self.assertEqual(kwargs.get("images_dir"), images_dir)

    @patch.object(ta, "check_ollama_available", return_value=True)
    @patch.object(ta, "find_browser_executable", return_value="dummy_browser")
    @patch.object(ta, "translate_single_pdf", return_value="/output/en/sample.pdf")
    def test_main_resolves_sibling_en_output_dir_from_subfolder(
        self, mock_translate, mock_browser, mock_ollama
    ):
        """Verify that main() sets output_dir to sibling 'en' when input folder is '.../board/de'."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            board_dir = os.path.join(tmp_dir, "Bayern")
            de_dir = os.path.join(board_dir, "de")
            images_dir = os.path.join(board_dir, "images")
            os.makedirs(de_dir, exist_ok=True)
            os.makedirs(images_dir, exist_ok=True)

            pdf_path = os.path.join(de_dir, "sample.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 content")

            with patch("sys.argv", ["translate-articles.py", "--input-folder", de_dir]):
                ta.main()

            mock_translate.assert_called_once()
            _, kwargs = mock_translate.call_args
            expected_en_dir = os.path.join(board_dir, "en")
            self.assertEqual(kwargs.get("output_dir"), expected_en_dir)

    @patch.object(ta, "check_ollama_available", return_value=True)
    @patch.object(ta, "find_browser_executable", return_value="dummy_browser")
    @patch.object(ta, "translate_single_pdf", return_value="/output/en/sample.pdf")
    def test_main_resolves_sibling_en_output_dir_from_board_folder(
        self, mock_translate, mock_browser, mock_ollama
    ):
        """Verify that main() detects PDFs in 'de/' and sets output_dir to 'en/' when input is board folder."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            board_dir = os.path.join(tmp_dir, "Bayern")
            de_dir = os.path.join(board_dir, "de")
            os.makedirs(de_dir, exist_ok=True)

            pdf_path = os.path.join(de_dir, "sample.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 content")

            with patch("sys.argv", ["translate-articles.py", "--input-folder", board_dir]):
                ta.main()

            mock_translate.assert_called_once()
            _, kwargs = mock_translate.call_args
            expected_en_dir = os.path.join(board_dir, "en")
            self.assertEqual(kwargs.get("output_dir"), expected_en_dir)


if __name__ == "__main__":
    unittest.main()
