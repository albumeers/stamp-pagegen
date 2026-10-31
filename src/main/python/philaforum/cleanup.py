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
Cleanup Utility for Philaforum Scraped HTML.
Performs post-scrape normalization and chrome cleanup on WoltLab thread HTML:
1. Deduplicates `messageList > li.modificationLogEntry` elements, retaining only
   the single entry with the `lastModificationLogEntry` class.
2. Fixes blockquote styling so that `display` is `block` instead of WoltLab's `grid`.
3. Strips unwanted external and inline `<script>` tags (WoltLabSuite, Google Tag Manager,
   tracking, and session initialization), while preserving custom scraper utility scripts.
"""

import argparse
import os
import re
import sys
from typing import Dict, List, Optional, Tuple


def find_modification_log_entries(html_text: str) -> List[Tuple[int, int, str]]:
    """
    Finds all `li.modificationLogEntry` elements in html_text.
    Returns list of (start_pos, end_pos, open_tag_string) tuples,
    properly accounting for nested <li> tags.
    """
    entries: List[Tuple[int, int, str]] = []
    open_pattern = re.compile(
        r'<li\b[^>]*class=["\'][^"\']*\bmodificationLogEntry\b[^"\']*["\'][^>]*>',
        re.IGNORECASE,
    )
    token_pattern = re.compile(r'(<li\b[^>]*>)|(</li\s*>)', re.IGNORECASE)

    for m in open_pattern.finditer(html_text):
        start_pos = m.start()
        content_start = m.end()

        # Skip if this match is inside an already identified entry
        if entries and start_pos < entries[-1][1]:
            continue

        depth = 1
        end_pos = None
        for tok in token_pattern.finditer(html_text, content_start):
            if tok.group(1):
                depth += 1
            elif tok.group(2):
                depth -= 1
                if depth == 0:
                    end_pos = tok.end()
                    break

        if end_pos is None:
            fallback_close = html_text.find("</li>", content_start)
            if fallback_close != -1:
                end_pos = fallback_close + 5
            else:
                end_pos = len(html_text)

        entries.append((start_pos, end_pos, m.group(0)))

    return entries


def clean_modification_log_entries(html_content: str) -> Tuple[str, int]:
    """
    Removes redundant `li.modificationLogEntry` elements from html_content,
    retaining only a single entry (specifically the one with the `lastModificationLogEntry` class).
    If multiple have `lastModificationLogEntry`, retains the latest (last) one.
    If none have `lastModificationLogEntry`, retains the latest (last) entry and ensures it has the class.
    Returns (cleaned_html, number_of_entries_removed).
    """
    if not html_content or "modificationLogEntry" not in html_content:
        return html_content, 0

    entries = find_modification_log_entries(html_content)
    if len(entries) <= 1:
        return html_content, 0

    # Determine which entry to keep
    last_mod_indices = [
        i for i, (_, _, open_tag) in enumerate(entries)
        if re.search(r'\blastModificationLogEntry\b', open_tag, re.IGNORECASE)
    ]

    if last_mod_indices:
        keep_idx = last_mod_indices[-1]
    else:
        keep_idx = len(entries) - 1

    entries_to_remove = [e for i, e in enumerate(entries) if i != keep_idx]
    if not entries_to_remove:
        return html_content, 0

    # Sort descending by start position to remove cleanly without offsetting indices
    entries_to_remove.sort(key=lambda x: x[0], reverse=True)

    cleaned = html_content
    for start_pos, end_pos, _ in entries_to_remove:
        # Check if preceding whitespace or trailing newline can be cleanly trimmed
        slice_start = start_pos
        while slice_start > 0 and cleaned[slice_start - 1] in " \t":
            slice_start -= 1
        if slice_start > 0 and cleaned[slice_start - 1] == "\n":
            slice_start -= 1

        slice_end = end_pos
        if slice_end < len(cleaned) and cleaned[slice_end] == "\n":
            slice_end += 1

        cleaned = cleaned[:slice_start] + cleaned[slice_end:]

    # Ensure the retained entry includes lastModificationLogEntry in its class attribute
    kept_start, kept_end, kept_open = entries[keep_idx]
    if not re.search(r'\blastModificationLogEntry\b', kept_open, re.IGNORECASE):
        new_open = re.sub(
            r'(class=["\'][^"\']*\bmodificationLogEntry\b)([^"\']*["\'])',
            r'\g<1> lastModificationLogEntry\2',
            kept_open,
            count=1,
            flags=re.IGNORECASE,
        )
        cleaned = cleaned.replace(kept_open, new_open, 1)

    return cleaned, len(entries_to_remove)


def fix_blockquote_display(html_content: str) -> Tuple[str, int]:
    """
    Fixes the blockquote display problem in WoltLab forum HTML:
    Ensures blockquotes (<blockquote class="quoteBox ...">) use `display: block`
    instead of WoltLab's default `display: grid`, preventing layout compression
    or clipping during viewing and PDF conversion.

    Applies to:
    1. Stylesheet rules in `<style id="scraper-print-stylesheet">` or general `<style>` blocks.
    2. Inline `style="..."` attributes on `<blockquote>` and `.quoteBox` elements.
    3. Injects a print stylesheet rule if missing.

    Returns (cleaned_html, number_of_fixes_applied).
    """
    if not html_content:
        return html_content, 0

    fixes_applied = 0
    updated_html = html_content

    # 1. Fix inline styles on <blockquote> and .quoteBox elements with display: grid
    def _fix_inline_style(match: re.Match) -> str:
        nonlocal fixes_applied
        tag_str = match.group(0)
        new_tag = re.sub(
            r'(\bstyle=["\'][^"\']*)\bdisplay\s*:\s*grid\b([^"\']*["\'])',
            r'\g<1>display: block\2',
            tag_str,
            flags=re.IGNORECASE,
        )
        if new_tag != tag_str:
            fixes_applied += 1
            return new_tag
        return tag_str

    inline_pattern = re.compile(
        r'<(?:blockquote\b[^>]*|div\b[^>]*\bclass=["\'][^"\']*\bquoteBox\b[^"\']*)[^>]*\bstyle=["\'][^"\']*display\s*:\s*grid[^"\']*["\'][^>]*>',
        re.IGNORECASE,
    )
    updated_html = inline_pattern.sub(_fix_inline_style, updated_html)

    # 2. Check and fix <style id="scraper-print-stylesheet">
    print_style_pattern = re.compile(
        r'(<style\b[^>]*\bid=["\']scraper-print-stylesheet["\'][^>]*>)(.*?)(</style>)',
        re.DOTALL | re.IGNORECASE,
    )
    print_style_match = print_style_pattern.search(updated_html)

    blockquote_block_css = (
        "blockquote, .quoteBox {\n"
        "            display: block !important;\n"
        "            grid-template-columns: none !important;\n"
        "            margin: 12px 0 !important;\n"
        "            padding: 10px 16px !important;\n"
        "            border-left: 4px solid #0066cc !important;\n"
        "            background-color: #f7f9fb !important;\n"
        "            color: #333333 !important;\n"
        "            font-style: italic !important;\n"
        "        }"
    )

    if print_style_match:
        open_tag = print_style_match.group(1)
        css_body = print_style_match.group(2)
        close_tag = print_style_match.group(3)

        # Check if display: grid is present in css_body for blockquote/.quoteBox
        new_css_body = re.sub(
            r'((?:blockquote|\.quoteBox)[^{]*\{[^}]*)\bdisplay\s*:\s*grid\b([^}]*\})',
            r'\g<1>display: block !important\2',
            css_body,
            flags=re.IGNORECASE,
        )

        # Check if blockquote rule is present
        bq_match = re.search(r'(blockquote(?:\s*,\s*\.quoteBox)?\s*\{)([^}]*)(\})', new_css_body, re.IGNORECASE)
        if bq_match:
            rule_selector = bq_match.group(1)
            rule_props = bq_match.group(2)
            rule_close = bq_match.group(3)

            # Check if display: block is already present
            if not re.search(r'\bdisplay\s*:\s*block\b', rule_props, re.IGNORECASE):
                # Ensure selector targets both blockquote and .quoteBox
                new_selector = "blockquote, .quoteBox {\n            display: block !important;\n            grid-template-columns: none !important;"
                # Also ensure .quoteBox is covered
                new_rule = f"        {new_selector}{rule_props}{rule_close}"
                new_css_body = (
                    new_css_body[:bq_match.start()]
                    + new_rule
                    + new_css_body[bq_match.end():]
                )
            elif ".quoteBox" not in rule_selector:
                # Add .quoteBox to selector
                new_selector = rule_selector.replace("blockquote", "blockquote, .quoteBox")
                new_css_body = (
                    new_css_body[:bq_match.start()]
                    + new_selector + rule_props + rule_close
                    + new_css_body[bq_match.end():]
                )
        else:
            # No blockquote rule at all in print stylesheet: add it
            new_css_body = f"{new_css_body.rstrip()}\n        {blockquote_block_css}\n    "

        if new_css_body != css_body:
            fixes_applied += 1
            updated_html = (
                updated_html[:print_style_match.start()]
                + f"{open_tag}{new_css_body}{close_tag}"
                + updated_html[print_style_match.end():]
            )
    else:
        # Check if the document has blockquotes or quoteBox, or any general WoltLab HTML
        has_blockquote = bool(
            re.search(r'<blockquote\b', updated_html, re.IGNORECASE)
            or re.search(r'class=["\'][^"\']*\bquoteBox\b', updated_html, re.IGNORECASE)
        )
        if has_blockquote:
            # Inject scraper-print-stylesheet with blockquote display: block
            injected_css = (
                f"\n    <style id=\"scraper-print-stylesheet\">\n"
                f"    @media screen, print {{\n"
                f"        {blockquote_block_css}\n"
                f"    }}\n"
                f"    </style>\n"
            )
            head_close = re.search(r'</head\s*>', updated_html, re.IGNORECASE)
            if head_close:
                updated_html = (
                    updated_html[:head_close.start()]
                    + injected_css
                    + updated_html[head_close.start():]
                )
                fixes_applied += 1
            else:
                body_open = re.search(r'<body\b[^>]*>', updated_html, re.IGNORECASE)
                if body_open:
                    updated_html = (
                        updated_html[:body_open.start()]
                        + injected_css
                        + updated_html[body_open.start():]
                    )
                    fixes_applied += 1
                else:
                    updated_html = injected_css + updated_html
                    fixes_applied += 1

    return updated_html, fixes_applied


def strip_unwanted_scripts(html_content: str, keep_scraper_scripts: bool = True) -> Tuple[str, int]:
    """
    Strips unwanted <script> tags from WoltLab forum HTML (both external scripts
    like WoltLabSuite.*.js, googletagmanager, and inline config/tracking scripts),
    preventing network delays, tracking, and console errors in offline/printable documents.

    If keep_scraper_scripts is True, preserves custom injected scripts whose id attribute
    starts with 'scraper-' (such as <script id="scraper-cleanup-wcf">).

    Returns (cleaned_html, number_of_scripts_removed).
    """
    if not html_content or "<script" not in html_content.lower():
        return html_content, 0

    removed_count = 0
    # Match <script ...>...</script> and self-closing <script .../>
    # Captures leading whitespace and trailing whitespace/newline to avoid leaving empty blank lines
    script_pattern = re.compile(
        r'([ \t]*)<script\b([^>]*?)(?:/>|>(.*?)</script>)([ \t]*(?:\r?\n)?)',
        re.DOTALL | re.IGNORECASE,
    )

    def _replace_script(match: re.Match) -> str:
        nonlocal removed_count
        attrs = match.group(2)
        trailing_space = match.group(4)

        if keep_scraper_scripts and re.search(r'\bid\s*=\s*["\']scraper-', attrs, re.IGNORECASE):
            return match.group(0)

        removed_count += 1
        # If the script tag was on its own line (has trailing newline), eliminate the trailing newline
        if trailing_space and ('\n' in trailing_space or '\r' in trailing_space):
            return ""
        return ""

    cleaned_html = script_pattern.sub(_replace_script, html_content)
    return cleaned_html, removed_count


def clean_html_file(file_path: str, dry_run: bool = False, strip_scripts: bool = True) -> Dict[str, int]:
    """
    Cleans a single HTML file by:
    1. Deduplicating `messageList > li.modificationLogEntry` elements.
    2. Fixing blockquote display (block instead of grid).
    3. Stripping unwanted <script> tags (WoltLab scripts, trackers, inline configs).

    Returns statistics dict:
    {'removed': int, 'blockquotes_fixed': int, 'scripts_removed': int, 'total': int}
    """
    empty_stats = {"removed": 0, "blockquotes_fixed": 0, "scripts_removed": 0, "total": 0}
    if not os.path.isfile(file_path):
        return empty_stats

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return empty_stats

    cleaned, removed_count = clean_modification_log_entries(content)
    cleaned, bq_count = fix_blockquote_display(cleaned)
    scripts_count = 0
    if strip_scripts:
        cleaned, scripts_count = strip_unwanted_scripts(cleaned)

    total_changes = removed_count + bq_count + scripts_count
    if total_changes > 0:
        if not dry_run:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(cleaned)
                details = []
                if removed_count > 0:
                    details.append(f"removed {removed_count} duplicate modification log(s)")
                if bq_count > 0:
                    details.append(f"fixed {bq_count} blockquote display rule(s)")
                if scripts_count > 0:
                    details.append(f"stripped {scripts_count} script tag(s)")
                print(f"  [CLEANED] {os.path.basename(file_path)}: {', '.join(details)}")
            except Exception as e:
                print(f"Error writing {file_path}: {e}")
                return empty_stats
        else:
            details = []
            if removed_count > 0:
                details.append(f"{removed_count} duplicate modification log(s)")
            if bq_count > 0:
                details.append(f"{bq_count} blockquote display rule(s)")
            if scripts_count > 0:
                details.append(f"{scripts_count} script tag(s)")
            print(f"  [DRY-RUN] Would clean {os.path.basename(file_path)}: {', '.join(details)}")

    return {
        "removed": removed_count,
        "blockquotes_fixed": bq_count,
        "scripts_removed": scripts_count,
        "total": total_changes,
    }


def clean_directory(
    directory: str,
    dry_run: bool = False,
    recursive: bool = True,
    strip_scripts: bool = True,
) -> Dict[str, int]:
    """
    Scans directory for HTML files and cleans duplicate modification log entries,
    fixes blockquote styling, and strips unwanted script tags.
    Returns statistics dict:
    {'scanned': int, 'modified': int, 'removed': int, 'blockquotes_fixed': int, 'scripts_removed': int}.
    """
    target_dir = os.path.abspath(directory)
    if not os.path.isdir(target_dir):
        print(f"Error: Directory not found: {target_dir}")
        return {"scanned": 0, "modified": 0, "removed": 0, "blockquotes_fixed": 0, "scripts_removed": 0}

    scanned_count = 0
    modified_count = 0
    total_removed = 0
    total_bq_fixed = 0
    total_scripts_removed = 0

    html_files: List[str] = []
    if recursive:
        for root, _, files in os.walk(target_dir):
            for f in files:
                if f.lower().endswith(".html"):
                    html_files.append(os.path.join(root, f))
    else:
        for f in os.listdir(target_dir):
            if f.lower().endswith(".html"):
                html_files.append(os.path.join(target_dir, f))

    html_files.sort()
    scanned_count = len(html_files)

    for fpath in html_files:
        stats = clean_html_file(fpath, dry_run=dry_run, strip_scripts=strip_scripts)
        if stats["total"] > 0:
            modified_count += 1
            total_removed += stats["removed"]
            total_bq_fixed += stats["blockquotes_fixed"]
            total_scripts_removed += stats["scripts_removed"]

    return {
        "scanned": scanned_count,
        "modified": modified_count,
        "removed": total_removed,
        "blockquotes_fixed": total_bq_fixed,
        "scripts_removed": total_scripts_removed,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Clean WoltLab thread HTML files: deduplicate modificationLogEntry elements, "
                    "fix blockquote display (block instead of grid), and strip unwanted script tags."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=None,
        help="Directory containing HTML files to clean",
    )
    parser.add_argument(
        "--dir",
        "-d",
        dest="dir_opt",
        help="Directory containing HTML files to clean (alternative to positional argument)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Preview files that would be modified without saving changes",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not scan subdirectories (default: recursive)",
    )
    parser.add_argument(
        "--no-strip-scripts",
        action="store_true",
        help="Do not strip JavaScript tags (default: strip unwanted external and inline scripts)",
    )

    args = parser.parse_args()
    target_dir = args.dir_opt or args.directory

    if not target_dir:
        parser.print_help()
        sys.exit(1)

    print(f"========================================================")
    print(f"Philaforum HTML Cleanup Utility")
    print(f"Target Directory: {os.path.abspath(target_dir)}")
    print(f"Mode: {'DRY-RUN (Preview Only)' if args.dry_run else 'ACTIVE (In-place modification)'}")
    print(f"Recursive: {not args.no_recursive}")
    print(f"Strip Scripts: {not args.no_strip_scripts}")
    print(f"========================================================")

    stats = clean_directory(
        directory=target_dir,
        dry_run=args.dry_run,
        recursive=not args.no_recursive,
        strip_scripts=not args.no_strip_scripts,
    )

    print(f"\nSummary:")
    print(f"  Files Scanned:              {stats['scanned']}")
    print(f"  Files Modified:             {stats['modified']}")
    print(f"  Log Entries Removed:        {stats['removed']}")
    print(f"  Blockquote Fixes Applied:   {stats['blockquotes_fixed']}")
    print(f"  Script Tags Stripped:       {stats['scripts_removed']}")
    print(f"========================================================")


if __name__ == "__main__":
    main()
