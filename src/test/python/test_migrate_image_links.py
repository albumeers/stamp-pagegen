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

"""Unit tests for src/main/python/scraper/migrate_image_links.py."""

import os
import sys
import tempfile
import unittest

import pypdf
from pypdf.generic import ArrayObject, DictionaryObject, FloatObject, NameObject, NumberObject, TextStringObject

# Ensure src/main/python is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../main/python")))

from scraper.migrate_image_links import (
    clean_image_filename,
    convert_image_uri,
    migrate_all,
    migrate_board_images,
    patch_pdf_file,
)


def create_test_pdf_with_link(pdf_path: str, link_uri: str):
    """Creates a minimal valid PDF containing a Link annotation with a /URI action."""
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=300, height=300)

    # Build action dictionary
    action = DictionaryObject()
    action[NameObject("/Type")] = NameObject("/Action")
    action[NameObject("/S")] = NameObject("/URI")
    action[NameObject("/URI")] = TextStringObject(link_uri)

    # Build link annotation
    annot = DictionaryObject()
    annot[NameObject("/Type")] = NameObject("/Annot")
    annot[NameObject("/Subtype")] = NameObject("/Link")
    rect = ArrayObject([FloatObject(10), FloatObject(10), FloatObject(100), FloatObject(50)])
    annot[NameObject("/Rect")] = rect
    annot[NameObject("/A")] = action

    # Attach annotation to page
    page[NameObject("/Annots")] = ArrayObject([annot])

    with open(pdf_path, "wb") as f:
        writer.write(f)


class TestMigrateImageLinks(unittest.TestCase):
    """Tests for migrate_image_links utility functions and batch workflows."""

    def test_clean_image_filename_with_percent_encoded_umlauts(self):
        raw = "413363-dr-158-pos-65-farbpunkte-%C3%BCber-dem-feld-mit-dem-lorbeer.jpg"
        expected = "413363-dr-158-pos-65-farbpunkte-ueber-dem-feld-mit-dem-lorbeer.jpg"
        self.assertEqual(clean_image_filename(raw), expected)

    def test_clean_image_filename_with_raw_umlauts(self):
        raw = "101437-pärchen-völkersbach-weiß.jpg"
        expected = "101437-paerchen-voelkersbach-weiss.jpg"
        self.assertEqual(clean_image_filename(raw), expected)

    def test_clean_image_filename_already_clean(self):
        clean = "1663-1.jpg"
        self.assertEqual(clean_image_filename(clean), clean)

    def test_convert_image_uri_absolute_file_uri(self):
        orig = "file:///D:/src/stamp-pagegen/output_pdfs/Deutsches-Reich-1872-1945/images/413363-%C3%BCber.jpg"
        expected = "../images/413363-ueber.jpg"
        self.assertEqual(convert_image_uri(orig), expected)

    def test_convert_image_uri_relative_uri(self):
        orig = "../images/105960-v%C3%B6lkersbach.jpg"
        expected = "../images/105960-voelkersbach.jpg"
        self.assertEqual(convert_image_uri(orig), expected)

    def test_convert_image_uri_legacy_images_folder(self):
        orig = "images/107371-verf%C3%A4rbt.jpg"
        expected = "../images/107371-verfaerbt.jpg"
        self.assertEqual(convert_image_uri(orig), expected)

    def test_convert_image_uri_non_image_unmodified(self):
        web_url = "https://philaforum.com/forum/thread/5790-bayern-3-kreuzer-blau/"
        self.assertIsNone(convert_image_uri(web_url))

    def test_migrate_board_images(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            images_dir = os.path.join(tmp_dir, "images")
            os.makedirs(images_dir, exist_ok=True)

            # Create test files
            old_file_1 = os.path.join(images_dir, "101437-p%C3%A4rchendr.jpg")
            clean_file = os.path.join(images_dir, "clean-image.png")

            with open(old_file_1, "wb") as f:
                f.write(b"data1")
            with open(clean_file, "wb") as f:
                f.write(b"data2")

            renamed = migrate_board_images(images_dir, dry_run=False)

            # Assert old file was renamed
            expected_new_1 = os.path.join(images_dir, "101437-paerchendr.jpg")
            self.assertTrue(os.path.isfile(expected_new_1))
            self.assertFalse(os.path.isfile(old_file_1))
            self.assertTrue(os.path.isfile(clean_file))
            self.assertIn("101437-p%C3%A4rchendr.jpg", renamed)
            self.assertEqual(renamed["101437-p%C3%A4rchendr.jpg"], "101437-paerchendr.jpg")

    def test_patch_pdf_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = os.path.join(tmp_dir, "test.pdf")
            orig_uri = "file:///D:/output/images/413363-%C3%BCber.jpg"
            create_test_pdf_with_link(pdf_path, orig_uri)

            # Patch PDF
            updates = patch_pdf_file(pdf_path, dry_run=False)
            self.assertEqual(updates, 1)

            # Verify with reader
            reader = pypdf.PdfReader(pdf_path)
            page = reader.pages[0]
            annots = page["/Annots"]
            annot_obj = annots[0].get_object()
            new_uri = str(annot_obj["/A"]["/URI"])
            self.assertEqual(new_uri, "../images/413363-ueber.jpg")

    def test_migrate_all_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            board_dir = os.path.join(tmp_dir, "TestBoard")
            images_dir = os.path.join(board_dir, "images")
            pdf_dir = os.path.join(board_dir, "de")
            os.makedirs(images_dir, exist_ok=True)
            os.makedirs(pdf_dir, exist_ok=True)

            # Setup image
            img_file = os.path.join(images_dir, "500-ausl%C3%A4ndisch.jpg")
            with open(img_file, "wb") as f:
                f.write(b"test image")

            # Setup PDF
            pdf_file = os.path.join(pdf_dir, "Thread.pdf")
            create_test_pdf_with_link(pdf_file, "file:///D:/workspace/output/images/500-ausl%C3%A4ndisch.jpg")

            stats = migrate_all(root_dir=tmp_dir, dry_run=False)

            self.assertEqual(stats["boards_processed"], 1)
            self.assertEqual(stats["images_renamed"], 1)
            self.assertEqual(stats["pdfs_scanned"], 1)
            self.assertEqual(stats["pdfs_modified"], 1)
            self.assertEqual(stats["uris_patched"], 1)

            # Check renamed image
            expected_img = os.path.join(images_dir, "500-auslaendisch.jpg")
            self.assertTrue(os.path.isfile(expected_img))
            self.assertFalse(os.path.isfile(img_file))

            # Check patched PDF URI
            reader = pypdf.PdfReader(pdf_file)
            page = reader.pages[0]
            uri = str(page["/Annots"][0].get_object()["/A"]["/URI"])
            self.assertEqual(uri, "../images/500-auslaendisch.jpg")


if __name__ == "__main__":
    unittest.main()
