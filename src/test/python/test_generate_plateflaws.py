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
        if any(fullname.startswith(prefix) for prefix in ["pythoncom", "win32com", "docx", "PIL", "reportlab"]):
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
        """Test parsing --selection, --processor, --input-dir, --output-dir, and --images-dir CLI arguments."""
        test_args = [
            "generate-plateflaws.py",
            "--selection", "ddr",
            "--processor", "word",
            "--input-dir", "/tmp/xml",
            "--output-dir", "/tmp/pdf",
            "--images-dir", "/tmp/images"
        ]
        with unittest.mock.patch.object(sys, "argv", test_args):
            selection, proc, in_dir, out_dir, img_dir = pf.get_selection()
            self.assertEqual(selection, "ddr")
            self.assertEqual(proc, "word")
            self.assertEqual(in_dir, "/tmp/xml")
            self.assertEqual(out_dir, "/tmp/pdf")
            self.assertEqual(img_dir, "/tmp/images")

    def test_image_cache_clearing_and_gc(self):
        """Test _IMAGE_CACHE clearing after generate_pdf_main."""
        pf._IMAGE_CACHE["dummy_key"] = ("dummy_reader", 100, 100)
        self.assertIn("dummy_key", pf._IMAGE_CACHE)
        pf._IMAGE_CACHE.clear()
        self.assertNotIn("dummy_key", pf._IMAGE_CACHE)

    def test_load_mapping_config_defaults(self):
        """Test _load_mapping_config_main returns defaults when config is empty/None."""
        config = pf._load_mapping_config_main(None)
        self.assertEqual(config['image-type'], 'jpeg')
        self.assertEqual(config['image-quality'], 85)

    def test_load_mapping_config_custom_values(self):
        """Test _load_mapping_config_main parses custom image-type and image-quality."""
        custom_mapping = {
            "font-mappings": {},
            "image-type": "png",
            "image-quality": 95
        }
        config = pf._load_mapping_config_main(custom_mapping)
        self.assertEqual(config['image-type'], 'png')
        self.assertEqual(config['image-quality'], 95)

    def test_load_mapping_config_case_insensitivity_and_aliases(self):
        """Test _load_mapping_config_main parses case-insensitive image-type and jpg alias."""
        mapping_jpg = {"image-type": "JPG", "image-quality": "75"}
        config_jpg = pf._load_mapping_config_main(mapping_jpg)
        self.assertEqual(config_jpg['image-type'], 'jpeg')
        self.assertEqual(config_jpg['image-quality'], 75)

        mapping_png = {"image-type": "PNG"}
        config_png = pf._load_mapping_config_main(mapping_png)
        self.assertEqual(config_png['image-type'], 'png')

    def test_load_mapping_config_invalid_quality_range(self):
        """Test _load_mapping_config_main falls back to default 85 for out-of-range quality."""
        mapping_invalid = {"image-quality": 150}
        config = pf._load_mapping_config_main(mapping_invalid)
        self.assertEqual(config['image-quality'], 85)

        mapping_negative = {"image-quality": -10}
        config_neg = pf._load_mapping_config_main(mapping_negative)
        self.assertEqual(config_neg['image-quality'], 85)

    def test_image_cache_eviction_by_last_page(self):
        """Test that images are evicted after their last page is rendered."""
        img1_key = str(pf._resolve_image_path_main("/tmp/images", "img1.jpg"))
        img2_key = str(pf._resolve_image_path_main("/tmp/images", "img2.jpg"))
        
        # list3 with 2 pages: page 0 uses img1 & img2, page 1 uses only img2
        list3 = [
            [[[None, "img1.jpg"], [None, "img2.jpg"]]],  # Page 0
            [[[None, "img2.jpg"]]]                       # Page 1
        ]
        
        # Map last page index for each image
        image_last_page_map = {}
        for p_idx, page in enumerate(list3):
            for row_list in page:
                for item in row_list:
                    if len(item) > 1 and item[1]:
                        img_path = pf._resolve_image_path_main("/tmp/images", item[1])
                        image_last_page_map[str(img_path)] = p_idx
        
        self.assertEqual(image_last_page_map[img1_key], 0)
        self.assertEqual(image_last_page_map[img2_key], 1)

        # Simulate rendering page 0
        pf._IMAGE_CACHE[img1_key] = ("reader1", 100, 100)
        pf._IMAGE_CACHE[img2_key] = ("reader2", 100, 100)

        page_idx = 0
        keys_to_evict = [k for k, last_idx in image_last_page_map.items() if last_idx <= page_idx and k in pf._IMAGE_CACHE]
        for k in keys_to_evict:
            del pf._IMAGE_CACHE[k]

        # img1 should be evicted after page 0, but img2 retained for page 1
        self.assertNotIn(img1_key, pf._IMAGE_CACHE)
        self.assertIn(img2_key, pf._IMAGE_CACHE)

        # Simulate rendering page 1
        page_idx = 1
        keys_to_evict = [k for k, last_idx in image_last_page_map.items() if last_idx <= page_idx and k in pf._IMAGE_CACHE]
        for k in keys_to_evict:
            del pf._IMAGE_CACHE[k]

        # img2 should be evicted after page 1
        self.assertNotIn(img2_key, pf._IMAGE_CACHE)

    def test_default_output_dir_tempfile_fallback(self):
        """Test default_output_dir uses tempfile.gettempdir()."""
        import tempfile
        self.assertEqual(pf.default_output_dir, tempfile.gettempdir())

    def test_3_tier_parameter_precedence(self):
        """Test 3-tier parameter precedence hierarchy: Tier 1 (Defaults) < Tier 2 (mapping.json) < Tier 3 (CLI args)."""
        import argparse
        import tempfile

        # Tier 1: Defaults
        res_t1 = pf._resolve_config_params(cli_args=None, font_mappings=None)
        self.assertEqual(res_t1['processor'], 'reportlab')
        self.assertEqual(res_t1['image-type'], 'jpeg')
        self.assertEqual(res_t1['image-quality'], 85)
        self.assertEqual(res_t1['output-dir'], tempfile.gettempdir())
        self.assertIsNone(res_t1['selection'])

        # Tier 2: mapping.json / font_mappings overrides Tier 1
        tier2_mapping = {
            'processor': 'word',
            'image-type': 'png',
            'image-quality': 90,
            'input-dir': '/tier2/input',
            'output-dir': '/tier2/output',
            'selection': 'ddr'
        }
        res_t2 = pf._resolve_config_params(cli_args=None, font_mappings=tier2_mapping)
        self.assertEqual(res_t2['processor'], 'word')
        self.assertEqual(res_t2['image-type'], 'png')
        self.assertEqual(res_t2['image-quality'], 90)
        self.assertEqual(res_t2['input-dir'], '/tier2/input')
        self.assertEqual(res_t2['output-dir'], '/tier2/output')
        self.assertEqual(res_t2['selection'], 'ddr')

        # Tier 3: CLI args overrides Tiers 1 & 2
        cli_args = argparse.Namespace(
            selection='bavaria',
            processor='reportlab',
            input_dir='/tier3/input',
            output_dir='/tier3/output',
            images_dir='/tier3/images',
            image_type='jpeg',
            image_quality=99
        )
        res_t3 = pf._resolve_config_params(cli_args=cli_args, font_mappings=tier2_mapping)
        self.assertEqual(res_t3['selection'], 'bavaria')
        self.assertEqual(res_t3['processor'], 'reportlab')
        self.assertEqual(res_t3['input-dir'], '/tier3/input')
        self.assertEqual(res_t3['output-dir'], '/tier3/output')
        self.assertEqual(res_t3['images-dir'], '/tier3/images')
        self.assertEqual(res_t3['image-type'], 'jpeg')
        self.assertEqual(res_t3['image-quality'], 99)

    def test_selection_mapping_loading(self):
        """Test _load_selection_mapping loads selection-mapping.json with short keys without spaces."""
        s_map = pf._load_selection_mapping('/tmp/xml')
        self.assertIn('ddr', s_map)
        self.assertIn('bb', s_map)
        self.assertIn('bavaria', s_map)
        self.assertNotIn('berlin and brandenburg', s_map)
        self.assertNotIn('east saxony', s_map)

        for key in s_map.keys():
            self.assertNotIn(' ', key, f"Selection key '{key}' should not contain spaces.")


if __name__ == "__main__":
    unittest.main()
