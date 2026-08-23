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

"""Unit tests for src/main/python/generate-plateflaws.py."""

import os
import sys
import json
import unittest
import importlib.util
from unittest.mock import MagicMock
from pathlib import Path

# Custom importer to dynamically mock missing optional/Windows dependencies (pythoncom, win32com, docx)
class DummyModule(MagicMock):
    __path__ = []

class CustomImporter:
    def find_spec(self, fullname, path, target=None):
        if any(fullname.startswith(prefix) for prefix in ["pythoncom", "win32com", "docx"]):
            return importlib.util.spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        return sys.modules.get(spec.name) or DummyModule()

    def exec_module(self, module):
        sys.modules[module.__name__] = module

sys.meta_path.insert(0, CustomImporter())

# Load generate-plateflaws.py dynamically due to hyphen in filename
MODULE_PATH = Path(__file__).resolve().parents[2] / "main" / "python" / "generator" / "generate-plateflaws.py"
spec = importlib.util.spec_from_file_location("generate_plateflaws", MODULE_PATH)
pf = importlib.util.module_from_spec(spec)
sys.modules["generate_plateflaws"] = pf
spec.loader.exec_module(pf)


class TestGeneratePlateflaws(unittest.TestCase):
    """Unit tests for utility and processing functions in generate-plateflaws.py."""

    def test_cleanUpPFDesc(self):
        """Test HTML entity replacement and leading whitespace trimming."""
        input_text = "   &quot;Flaw Description&quot;\\nLine 2"
        expected = '"Flaw Description"\nLine 2'
        self.assertEqual(pf.cleanUpPFDesc(input_text), expected)

        # Test string with leading spaces and newlines
        input_whitespace = "\n\t  Some text"
        self.assertEqual(pf.cleanUpPFDesc(input_whitespace), "Some text")

    def test_cleanUpPathName(self):
        """Test normalization of file path separators and trailing backslashes."""
        raw_path = "   C:/Stamps/images/folder/   "
        expected = "C:\\\\Stamps\\\\images\\\\folder"
        self.assertEqual(pf.cleanUpPathName(raw_path), expected)

        # Test double backslashes at end
        double_backslash_path = "D:/path/to/dir\\\\"
        self.assertEqual(pf.cleanUpPathName(double_backslash_path), "D:\\\\path\\\\to\\\\dir")

    def test_splitCombinedXML(self):
        """Test splitting XML strings into element fragments."""
        xml = "<album><page id='1'><set name='test'/></page></album>"
        result = pf.splitCombinedXML(xml)
        expected = ["<album>", "<page id='1'>", "<set name='test'/>", "</page>", "</album>"]
        self.assertEqual(result, expected)

    def test_create_file_list(self):
        """Test combining directory path and list of filenames."""
        directory = "C:\\Data\\XML"
        filenames = ["file1.xml", "file2.xml"]
        expected = [
            os.path.join(directory, "file1.xml"),
            os.path.join(directory, "file2.xml"),
        ]
        self.assertEqual(pf.create_file_list(directory, filenames), expected)

    def test_removeDenominationColor(self):
        """Test filtering data rows to only those with empty denomination, color, and cell desc."""
        # Row format indices in generate-plateflaws.py:
        # i_denomination = 3, i_color = 4, i_cell_desc = 5
        valid_row = ['data', 'images/stamp1.png', '18x18', '', '', '', '', '', '']
        invalid_denom = ['data', 'images/stamp2.png', '18x18', '10c', '', '', '', '', '']
        invalid_color = ['data', 'images/stamp3.png', '18x18', '', 'Red', '', '', '', '']
        invalid_desc = ['data', 'images/stamp4.png', '18x18', '', '', 'Defect', '', '', '']

        data_list = [valid_row, invalid_denom, invalid_color, invalid_desc]
        filtered = pf.removeDenominationColor(data_list)
        self.assertEqual(filtered, [valid_row])

    def test_remove_duplicates_from_data_list(self):
        """Test deduplication of data rows preserving order based on image and description indices."""
        i_image = 1
        i_rdesc = 3
        row1 = ['data', 'img1.png', '18x18', 'Flaw A']
        row2 = ['data', 'img2.png', '18x18', 'Flaw B']
        row3 = ['data', 'img1.png', '18x18', 'Flaw A']  # Duplicate of row1
        row4 = ['data', 'img1.png', '18x18', 'Flaw C']  # Different desc

        data_list = [row1, row2, row3, row4]
        deduped = pf.remove_duplicates_from_data_list(data_list, i_image, i_rdesc)
        self.assertEqual(deduped, [row1, row2, row4])

    def test_append_row_set_description(self):
        """Test appending row_set_description and issue year to data entries."""
        data_list = [
            ['row_set_description', 'Plate Flaw 1'],
            ['set', '1965 DDR Stamps'],
            ['data', 'images/stamp1.png', '18x18', '', '', '', '', '', ''],
            ['data', 'images/stamp_label.png', '18x18', '', '', '', '', '', ''],  # contains 'label', skipped
        ]
        result = pf.append_row_set_description(data_list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][-2], 'Plate Flaw 1')
        self.assertEqual(result[0][-1], '1965 DDR Stamps')

    def test_capture_raw_constant_plate_flaw_data(self):
        """Test capturing XML fragments matching active constant_title."""
        pf.constant_title = "Constant Plate Flaws"
        raw_xml = [
            '<page id="1">',
            '<set issue="Other">',
            '</page>',
            '<page id="2">',
            '<set issue="Constant Plate Flaws 1965">',
            '<s image="img1.png"/>',
            '</page>',
        ]
        captured = pf.capture_raw_constant_plate_flaw_data(raw_xml)
        self.assertIn('<set issue="Constant Plate Flaws 1965">', captured)
        self.assertIn('<s image="img1.png"/>', captured)
        self.assertNotIn('<set issue="Other">', captured)

    def test_resolve_image_path_main(self):
        """Test resolution of image paths relative to images directory parent."""
        images_dir = Path("/tmp/workspace/xml/images")
        image_field = "images/Germany/stamp.png"
        resolved = pf._resolve_image_path_main(images_dir, image_field)
        expected = (Path("/tmp/workspace/xml") / image_field).resolve()
        self.assertEqual(resolved, expected)

    def test_register_fonts_main_explicit_dict(self):
        """Test registering fonts with explicit dictionary mapping."""
        dummy_font = Path(__file__).resolve()
        font_map = {"TestFont": str(dummy_font)}
        # Should not raise exception
        pf._register_fonts_main(font_map)

    def test_register_fonts_main_object_structure(self):
        """Test registering fonts with 'font-mappings' object/dict key."""
        dummy_font = Path(__file__).resolve()
        font_obj = {"font-mappings": {"TestFontObj": str(dummy_font)}}
        pf._register_fonts_main(font_obj)

    def test_register_fonts_main_json_file(self):
        """Test registering fonts from a local mapping.json file when font_mappings is None."""
        dummy_font = Path(__file__).resolve()
        mapping_data = {"font-mappings": {"TestFontJSON": str(dummy_font)}}
        json_path = Path("mapping.json")
        created = False
        try:
            if not json_path.exists():
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(mapping_data, f)
                created = True

            pf._register_fonts_main(None)
        finally:
            if created and json_path.exists():
                json_path.unlink()


    def test_register_fonts_main_userprofile_env_var(self):
        """Test registering fonts with %USERPROFILE% environment variable expansion."""
        dummy_font = Path(__file__).resolve()
        try:
            relative_to_home = dummy_font.relative_to(Path.home())
            font_map = {"TestFontEnv": f"%USERPROFILE%/{relative_to_home}"}
        except ValueError:
            font_map = {"TestFontEnv": str(dummy_font)}
    def test_get_selection_cli_directory_args(self):
        """Test parsing --input-dir, --output-dir, and --images-dir CLI arguments."""
        test_args = [
            "generate-plateflaws.py",
            "--selection", "ddr",
            "--input-dir", "/tmp/xml",
            "--output-dir", "/tmp/pdf",
            "--images-dir", "/tmp/images"
        ]
        with unittest.mock.patch.object(sys, "argv", test_args):
            selection, backend, in_dir, out_dir, img_dir = pf.get_selection()
            self.assertEqual(selection, "ddr")
            self.assertEqual(backend, "reportlab")
            self.assertEqual(in_dir, "/tmp/xml")
            self.assertEqual(out_dir, "/tmp/pdf")
            self.assertEqual(img_dir, "/tmp/images")

    def test_image_cache_clearing_and_gc(self):
        """Test _IMAGE_CACHE clearing after generate_pdf_main."""
        pf._IMAGE_CACHE["dummy_key"] = ("dummy_reader", 100, 100)
        self.assertIn("dummy_key", pf._IMAGE_CACHE)
        pf._IMAGE_CACHE.clear()
        self.assertNotIn("dummy_key", pf._IMAGE_CACHE)


if __name__ == "__main__":
    unittest.main()
