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
migrate_image_links.py

Batch migration tool for stamp-pagegen forum PDFs and downloaded images:
1. Renames downloaded images containing percent-encoded sequences (e.g. %C3%BC)
   or raw German umlauts (ä, ö, ü, ß) into clean, standard ASCII transliterations
   (ae, oe, ue, ss) with no percent signs.
2. In-place patches PDF link annotations (/URI) in existing PDFs:
   - Converts old absolute file:///.../images/<file> paths to portable relative ../images/<file>.
   - Updates any image filenames in link annotations to the clean transliterated ASCII name.
"""

import argparse
import os
import re
import sys
import tempfile
import urllib.parse
from typing import Dict, List, Optional, Tuple

import pypdf
from pypdf.generic import NameObject, TextStringObject

try:
    from philaforum_scraper import GERMAN_TRANSLITERATION, transliterate_german
except ImportError:
    from scraper.philaforum_scraper import GERMAN_TRANSLITERATION, transliterate_german


def clean_image_filename(filename: str) -> str:
    """
    Translates a filename with percent-encoding or German umlauts to clean ASCII.
    Example: '413363-dr-158-pos-65-farbpunkte-%C3%BCber-dem-feld.jpg'
             -> '413363-dr-158-pos-65-farbpunkte-ueber-dem-feld.jpg'
    """
    if not filename:
        return ""
    # Unquote percent-encoding
    try:
        decoded = urllib.parse.unquote(filename)
    except Exception:
        decoded = filename

    # Transliterate German umlauts
    trans = transliterate_german(decoded)

    # Strip percent characters and invalid filesystem/URI chars
    clean = re.sub(r'[\\/*?:"<>|%]', "", trans).strip()
    return clean


def migrate_board_images(images_dir: str, dry_run: bool = False) -> Dict[str, str]:
    """
    Scans images_dir and renames files with percent-encoding or umlauts to clean ASCII names.
    Returns a dictionary mapping {old_filename: new_filename}.
    """
    renamed: Dict[str, str] = {}
    if not os.path.isdir(images_dir):
        return renamed

    for fname in sorted(os.listdir(images_dir)):
        old_path = os.path.join(images_dir, fname)
        if not os.path.isfile(old_path):
            continue

        target_name = clean_image_filename(fname)
        if target_name != fname:
            target_path = os.path.join(images_dir, target_name)
            renamed[fname] = target_name
            if not dry_run:
                try:
                    if os.path.isfile(target_path):
                        # Target already exists: if identical or target is valid, remove legacy duplicate
                        if os.path.getsize(target_path) >= os.path.getsize(old_path):
                            os.remove(old_path)
                        else:
                            os.replace(old_path, target_path)
                    else:
                        os.rename(old_path, target_path)
                except Exception as e:
                    print(f"  Warning: Could not rename '{fname}' -> '{target_name}': {e}", file=sys.stderr)

    return renamed


def convert_image_uri(uri: str) -> Optional[str]:
    """
    Converts an image URI (e.g. file:///.../images/<file> or ../images/<file>)
    to portable relative ../images/<clean_transliterated_name>.
    Returns the new URI if changed, or None if no change is required.
    """
    if not uri:
        return None

    # Only process image links (must contain /images/ or end with an image extension)
    is_image = "/images/" in uri or re.search(r"\.(jpe?g|png|gif|webp)(?:[?#]|$)", uri, re.IGNORECASE)
    if not is_image:
        return None

    # Extract image filename from URI
    if "/images/" in uri:
        raw_fname = uri.split("/images/")[-1].split("?")[0].split("#")[0]
    else:
        raw_fname = uri.split("/")[-1].split("?")[0].split("#")[0]

    clean_fname = clean_image_filename(raw_fname)
    target_uri = f"../images/{clean_fname}"

    if target_uri != uri:
        return target_uri
    return None


def patch_pdf_file(pdf_path: str, dry_run: bool = False) -> int:
    """
    Inspects and patches link annotations in a single PDF file.
    Updates any image URI to relative ../images/<clean_filename>.
    Returns the count of patched URIs (0 if unmodified).
    """
    if not os.path.isfile(pdf_path):
        return 0

    try:
        reader = pypdf.PdfReader(pdf_path)
    except Exception as e:
        print(f"  Warning: Could not read PDF '{pdf_path}': {e}", file=sys.stderr)
        return 0

    modified = False
    uri_updates_count = 0

    try:
        writer = pypdf.PdfWriter()
        writer.clone_document_from_reader(reader)

        for page in writer.pages:
            if "/Annots" in page:
                annots = page["/Annots"]
                for annot in annots:
                    annot_obj = annot.get_object()
                    if "/A" in annot_obj and "/URI" in annot_obj["/A"]:
                        orig_uri = str(annot_obj["/A"]["/URI"])
                        new_uri = convert_image_uri(orig_uri)
                        if new_uri and new_uri != orig_uri:
                            annot_obj["/A"][NameObject("/URI")] = TextStringObject(new_uri)
                            modified = True
                            uri_updates_count += 1

        if modified and not dry_run:
            # Write to a temporary file in the same directory for atomic replace
            pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
            with tempfile.NamedTemporaryFile(dir=pdf_dir, suffix=".tmp.pdf", delete=False) as tf:
                tmp_name = tf.name
                writer.write(tf)
            os.replace(tmp_name, pdf_path)

    except Exception as e:
        print(f"  Warning: Error processing PDF '{pdf_path}': {e}", file=sys.stderr)
        return 0

    return uri_updates_count


def migrate_all(
    root_dir: str = "output_pdfs",
    board_filter: Optional[str] = None,
    dry_run: bool = False,
    skip_images: bool = False,
    skip_pdfs: bool = False,
    verbose: bool = False,
) -> Dict[str, int]:
    """
    Performs full migration across root_dir:
    1. Renames image files in <board>/images/.
    2. Patches link annotations in all PDFs under <board>/.
    """
    stats = {
        "boards_processed": 0,
        "images_renamed": 0,
        "pdfs_scanned": 0,
        "pdfs_modified": 0,
        "uris_patched": 0,
    }

    if not os.path.isdir(root_dir):
        print(f"Error: Root directory '{root_dir}' does not exist.", file=sys.stderr)
        return stats

    board_dirs = []
    for entry in sorted(os.listdir(root_dir)):
        full = os.path.join(root_dir, entry)
        if os.path.isdir(full) and not entry.startswith("."):
            if board_filter and entry.lower() != board_filter.lower():
                continue
            board_dirs.append(full)

    for bdir in board_dirs:
        bname = os.path.basename(bdir)
        print(f"\n========================================")
        print(f"Processing Board: {bname}")
        print(f"========================================")
        stats["boards_processed"] += 1

        # Step 1: Images
        images_dir = os.path.join(bdir, "images")
        if not skip_images and os.path.isdir(images_dir):
            renamed = migrate_board_images(images_dir, dry_run=dry_run)
            stats["images_renamed"] += len(renamed)
            if renamed:
                print(f"  Renamed {len(renamed)} image(s) in {images_dir}")
                if verbose:
                    for old_n, new_n in list(renamed.items())[:10]:
                        print(f"    '{old_n}' -> '{new_n}'")
                    if len(renamed) > 10:
                        print(f"    ... and {len(renamed) - 10} more.")
            else:
                print(f"  All images in {images_dir} are clean.")

        # Step 2: PDFs
        if not skip_pdfs:
            board_pdfs = []
            for root, _, files in os.walk(bdir):
                for f in files:
                    if f.lower().endswith(".pdf") and not f.startswith("."):
                        board_pdfs.append(os.path.join(root, f))

            modified_in_board = 0
            uris_in_board = 0
            for pdf_p in board_pdfs:
                stats["pdfs_scanned"] += 1
                patched = patch_pdf_file(pdf_p, dry_run=dry_run)
                if patched > 0:
                    modified_in_board += 1
                    uris_in_board += patched
                    stats["pdfs_modified"] += 1
                    stats["uris_patched"] += patched
                    if verbose:
                        print(f"  [PATCHED] {os.path.basename(pdf_p)} ({patched} URI updates)")

            print(f"  Scanned {len(board_pdfs)} PDF(s): {modified_in_board} modified ({uris_in_board} URIs patched).")

    return stats


def parse_arguments(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate percent-encoded and umlaut image filenames and patch PDF URIs to portable relative paths.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--root-dir",
        default="output_pdfs",
        help="Root folder containing scraped boards and PDFs.",
    )
    parser.add_argument(
        "--board",
        default=None,
        help="Optional specific board folder name to migrate (e.g. 'Deutsches-Reich-1872-1945').",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate changes without renaming files or modifying PDFs.",
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip renaming image files on disk.",
    )
    parser.add_argument(
        "--skip-pdfs",
        action="store_true",
        help="Skip patching PDF link annotations.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print verbose per-file migration logs.",
    )
    return parser.parse_args(argv)


def main():
    args = parse_arguments()
    mode_str = " [DRY-RUN]" if args.dry_run else ""
    print(f"Starting image link migration{mode_str} in '{args.root_dir}'...")

    stats = migrate_all(
        root_dir=args.root_dir,
        board_filter=args.board,
        dry_run=args.dry_run,
        skip_images=args.skip_images,
        skip_pdfs=args.skip_pdfs,
        verbose=args.verbose,
    )

    print("\n========================================")
    print("Migration Summary:")
    print(f"  Boards Processed : {stats['boards_processed']}")
    print(f"  Images Renamed   : {stats['images_renamed']}")
    print(f"  PDFs Scanned     : {stats['pdfs_scanned']}")
    print(f"  PDFs Modified    : {stats['pdfs_modified']}")
    print(f"  URIs Patched     : {stats['uris_patched']}")
    print("========================================")


if __name__ == "__main__":
    main()
