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
Thread Page Splitter Utility.
Splits large WoltLab thread HTML files into multi-part HTML documents based on
a configurable post count threshold (default: 2500 posts).

Features:
- Naming convention: Part 1 retains base name {stem}.html, parts 2+ get zero-padded {stem}-Part02.html, etc.
- Adds '< Previous' and 'Next >' pagination navigation links at the bottom of each page.
- Ensures each split page retains the footer containing the thread's last modified date
  (preserving or synthesizing the lastModificationLogEntry element).
- Updates <title> and <h1> content header with part badges.
- Preserves document chrome, styles, and script tags cleanly.
"""

import argparse
from datetime import datetime, timezone
import math
import os
import re
import sys
from typing import Dict, List, Optional, Tuple


DEFAULT_POSTS_PER_PAGE = 2500


def extract_last_modified_info(html_content: str, file_path: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts the last modified ISO datetime and human-readable date string from:
    1. An existing li.modificationLogEntry element
    2. The publication / modified time of the last post
    3. File modification timestamp on disk (fallback)
    Returns (iso_date, display_date).
    """
    # 1. Check existing li.modificationLogEntry
    mod_match = re.search(
        r'<li\b[^>]*class=["\'][^"\']*\bmodificationLogEntry\b[^"\']*["\'][^>]*>(.*?)</li>',
        html_content,
        re.DOTALL | re.IGNORECASE,
    )
    if mod_match:
        dt_match = re.search(
            r'<woltlab-core-date-time\b[^>]*\bdate=["\']([^"\']+)["\'][^>]*>(.*?)</woltlab-core-date-time>',
            mod_match.group(1),
            re.IGNORECASE,
        )
        if dt_match:
            return dt_match.group(1), dt_match.group(2).strip()

    # 2. Check publication time of last post in the document
    time_matches = list(
        re.finditer(
            r'<woltlab-core-date-time\b[^>]*\bdate=["\']([^"\']+)["\'][^>]*>(.*?)</woltlab-core-date-time>',
            html_content,
            re.IGNORECASE,
        )
    )
    if time_matches:
        last_match = time_matches[-1]
        return last_match.group(1), last_match.group(2).strip()

    # Check <time datetime="...">
    time_matches2 = list(re.finditer(r'<time\b[^>]*\bdatetime=["\']([^"\']+)["\'][^>]*>(.*?)</time>', html_content, re.IGNORECASE))
    if time_matches2:
        last_match = time_matches2[-1]
        return last_match.group(1), last_match.group(2).strip()

    # 3. File fallback
    if file_path and os.path.isfile(file_path):
        mtime = os.path.getmtime(file_path)
        dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        return dt.isoformat(), dt.strftime("%d. %B %Y, %H:%M")

    now = datetime.now(timezone.utc)
    return now.isoformat(), now.strftime("%d. %B %Y, %H:%M")


def extract_or_build_modification_log(html_content: str, file_path: Optional[str] = None) -> str:
    """
    Extracts the existing `li.modificationLogEntry` (specifically lastModificationLogEntry)
    from html_content, or synthesizes a clean one from the thread's last modified date.
    """
    # Check if a modificationLogEntry already exists in the document
    if "modificationLogEntry" in html_content:
        open_pattern = re.compile(
            r'<li\b[^>]*class=["\'][^"\']*\bmodificationLogEntry\b[^"\']*["\'][^>]*>',
            re.IGNORECASE,
        )
        mod_matches = []
        for m in open_pattern.finditer(html_content):
            c_pos = html_content.find("</li>", m.end())
            if c_pos != -1:
                mod_matches.append(html_content[m.start():c_pos + 5].strip())

        if mod_matches:
            # Prefer the one with lastModificationLogEntry class
            for tag in reversed(mod_matches):
                if "lastmodificationlogentry" in tag.lower():
                    return tag
            # Fall back to the last found modificationLogEntry
            log_html = mod_matches[-1]
            if "lastmodificationlogentry" not in log_html.lower():
                log_html = re.sub(
                    r'(class=["\'][^"\']*\bmodificationLogEntry\b)([^"\']*["\'])',
                    r'\g<1> lastModificationLogEntry\2',
                    log_html,
                    count=1,
                    flags=re.IGNORECASE,
                )
            return log_html

    # Synthesize clean modificationLogEntry footer note
    iso_date, display_date = extract_last_modified_info(html_content, file_path=file_path)
    iso_val = iso_date or ""
    disp_val = display_date or iso_val

    return (
        f'<li class="modificationLogEntry lastModificationLogEntry" data-is-summarized="0">\n'
        f'    <article class="message messageReduced">\n'
        f'        <div class="messageContent">\n'
        f'            <div class="messageHeader">\n'
        f'                <div class="box32 messageHeaderWrapper">\n'
        f'                    <div class="messageHeaderBox">\n'
        f'                        <h2 class="messageTitle">\n'
        f'                            <span class="messageTitleText">Letzte Änderung / Last Modified</span>\n'
        f'                            <small class="separatorLeft"><woltlab-core-date-time date="{iso_val}">{disp_val}</woltlab-core-date-time></small>\n'
        f'                        </h2>\n'
        f'                    </div>\n'
        f'                </div>\n'
        f'            </div>\n'
        f'        </div>\n'
        f'    </article>\n'
        f'</li>'
    )


def extract_thread_components(html_content: str) -> Tuple[str, List[str], str, Optional[str]]:
    """
    Parses a thread HTML document into:
    - header_html: everything up to inner messageList opening
    - posts: list of individual post HTML strings (excluding modification log)
    - footer_html: everything from closing </ul> onward
    - mod_log_html: the extracted modificationLogEntry if present
    """
    ul_match = re.search(r'<ul\b[^>]*\bclass=["\'][^"\']*\bmessageList\b[^"\']*["\'][^>]*>', html_content, re.IGNORECASE)
    if not ul_match:
        # Fallback: find <article class="...message...">
        art_matches = list(re.finditer(r'<article\b[^>]*\bclass=["\'][^"\']*\bmessage\b[^"\']*["\'][^>]*>.*?</article>', html_content, re.DOTALL | re.IGNORECASE))
        if not art_matches:
            return html_content, [], "", None
        header_html = html_content[:art_matches[0].start()]
        posts = [m.group(0).strip() for m in art_matches]
        footer_html = html_content[art_matches[-1].end():]
        return header_html, posts, footer_html, None

    header_end = ul_match.end()
    header_html = html_content[:header_end]

    # Find closing </ul> matching the messageList container via depth tracking
    token_pattern = re.compile(r'(<ul\b[^>]*>)|(</ul\s*>)', re.IGNORECASE)
    depth = 1
    ul_close_pos = len(html_content)

    for m in token_pattern.finditer(html_content, header_end):
        if m.group(1):
            depth += 1
        elif m.group(2):
            depth -= 1
            if depth == 0:
                ul_close_pos = m.start()
                break

    inner_content = html_content[header_end:ul_close_pos]
    footer_html = html_content[ul_close_pos:]

    # Check for modificationLogEntry in inner_content efficiently without catastrophic backtracking
    mod_log_html: Optional[str] = None
    if "modificationLogEntry" in inner_content:
        mod_open = re.search(r'<li\b[^>]*class=["\'][^"\']*\bmodificationLogEntry\b[^"\']*["\'][^>]*>', inner_content, re.IGNORECASE)
        if mod_open:
            close_pos = inner_content.find("</li>", mod_open.end())
            if close_pos != -1:
                mod_log_html = inner_content[mod_open.start():close_pos + 5].strip()
                inner_content = inner_content[:mod_open.start()] + inner_content[close_pos + 5:]

    # Find posts inside inner_content
    post_pattern = re.compile(r'<li\b[^>]*\bid=["\']post\d+["\']', re.IGNORECASE)
    matches = list(post_pattern.finditer(inner_content))

    posts: List[str] = []
    if matches:
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(inner_content)
            post_str = inner_content[start:end].strip()
            if post_str:
                posts.append(post_str)
    else:
        # Fallback to <article ... message> inside inner_content
        art_pattern = re.compile(r'<article\b[^>]*\bclass=["\'][^"\']*\bmessage\b[^"\']*["\'][^>]*>.*?</article>', re.DOTALL | re.IGNORECASE)
        art_matches = list(art_pattern.finditer(inner_content))
        if art_matches:
            posts = [m.group(0).strip() for m in art_matches]
        else:
            # Fallback to <li> elements
            li_pattern = re.compile(r'<li\b[^>]*>.*?</li>', re.DOTALL | re.IGNORECASE)
            li_matches = list(li_pattern.finditer(inner_content))
            posts = [m.group(0).strip() for m in li_matches]

    return header_html, posts, footer_html, mod_log_html


def build_pagination_nav(
    prev_filename: Optional[str],
    next_filename: Optional[str],
    current_part: int,
    total_parts: int,
    post_start: int,
    post_end: int,
    total_posts: int,
) -> str:
    """
    Constructs clean pagination navigation HTML with '< Previous' and 'Next >' links.
    """
    prev_link = ""
    if prev_filename:
        prev_link = (
            f'<a href="{prev_filename}" class="prevPageLink" '
            f'style="display: inline-block; padding: 6px 14px; background-color: #ffffff; '
            f'border: 1px solid #c0d0e0; border-radius: 4px; color: #0066cc; '
            f'text-decoration: none; font-weight: 600; font-size: 11pt;">'
            f'&lt; Previous</a>'
        )

    next_link = ""
    if next_filename:
        next_link = (
            f'<a href="{next_filename}" class="nextPageLink" '
            f'style="display: inline-block; padding: 6px 14px; background-color: #0066cc; '
            f'border: 1px solid #0055aa; border-radius: 4px; color: #ffffff; '
            f'text-decoration: none; font-weight: 600; font-size: 11pt;">'
            f'Next &gt;</a>'
        )

    info_text = (
        f'Teil {current_part} von {total_parts} &bull; '
        f'Part {current_part} of {total_parts} '
        f'<span style="color: #888888; font-size: 9.5pt;">(Posts {post_start:,} – {post_end:,} / {total_posts:,})</span>'
    )

    return (
        f'\n<!-- Thread Pagination Navigation -->\n'
        f'<nav class="threadPagination" '
        f'style="display: flex; justify-content: space-between; align-items: center; '
        f'margin: 28px 0 20px 0; padding: 12px 18px; background-color: #f7f9fb; '
        f'border: 1px solid #d0d7de; border-radius: 6px; '
        f'font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif;">\n'
        f'    <div class="paginationPrev" style="min-width: 120px; text-align: left;">{prev_link}</div>\n'
        f'    <div class="paginationInfo" style="color: #333333; font-size: 10.5pt; font-weight: 500; text-align: center;">{info_text}</div>\n'
        f'    <div class="paginationNext" style="min-width: 120px; text-align: right;">{next_link}</div>\n'
        f'</nav>\n'
    )


def update_page_titles(header_html: str, current_part: int, total_parts: int) -> str:
    """
    Updates <title> and <h1 class="contentTitle"> to include (Part X of Y) badge.
    """
    badge_text = f" (Part {current_part} of {total_parts})"

    # Update <title>
    title_match = re.search(r'(<title\b[^>]*>)(.*?)(</title>)', header_html, re.IGNORECASE | re.DOTALL)
    if title_match:
        open_t, inner_t, close_t = title_match.group(1), title_match.group(2), title_match.group(3)
        # Avoid duplicating if already present
        if not re.search(r'\(Part\s*\d+\s*of\s*\d+\)', inner_t, re.IGNORECASE):
            # If title contains ' - ', insert before the first hyphen separator
            if " - " in inner_t:
                parts = inner_t.split(" - ", 1)
                new_inner = f"{parts[0]}{badge_text} - {parts[1]}"
            else:
                new_inner = f"{inner_t}{badge_text}"
            header_html = header_html[:title_match.start()] + f"{open_t}{new_inner}{close_t}" + header_html[title_match.end():]

    # Update <h1 class="contentTitle">
    h1_match = re.search(r'(<h1\b[^>]*class=["\'][^"\']*\bcontentTitle\b[^"\']*["\'][^>]*>)(.*?)(</h1>)', header_html, re.IGNORECASE | re.DOTALL)
    if h1_match:
        open_h, inner_h, close_h = h1_match.group(1), h1_match.group(2), h1_match.group(3)
        if not re.search(r'class=["\'][^"\']*\bpartBadge\b', inner_h, re.IGNORECASE):
            badge_html = f' <span class="partBadge" style="font-size: 14pt; color: #555555; font-weight: normal;">(Part {current_part} of {total_parts})</span>'
            new_inner = f"{inner_h.strip()}{badge_html}"
            header_html = header_html[:h1_match.start()] + f"{open_h}{new_inner}{close_h}" + header_html[h1_match.end():]

    return header_html


def split_html_file(
    file_path: str,
    output_dir: Optional[str] = None,
    posts_per_page: int = DEFAULT_POSTS_PER_PAGE,
    dry_run: bool = False,
) -> Dict[str, object]:
    """
    Splits a single thread HTML file into multi-part files if post count exceeds posts_per_page.
    Option A zero-padded part naming: {stem}-Part01.html, {stem}-Part02.html, etc.

    Returns dict with summary statistics.
    """
    abs_path = os.path.abspath(file_path)
    if not os.path.isfile(abs_path):
        print(f"Error: File not found: {abs_path}")
        return {"file": file_path, "status": "error", "error": "file not found"}

    target_dir = os.path.abspath(output_dir) if output_dir else os.path.dirname(abs_path)
    os.makedirs(target_dir, exist_ok=True)

    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
        html_content = f.read()

    header_html, posts, footer_html, existing_mod_log = extract_thread_components(html_content)
    total_posts = len(posts)

    if total_posts <= posts_per_page:
        print(f"  [SKIPPED] {os.path.basename(abs_path)}: {total_posts} post(s) <= threshold ({posts_per_page})")
        return {
            "file": file_path,
            "status": "skipped",
            "posts": total_posts,
            "parts": 1,
            "generated_files": [],
        }

    total_parts = math.ceil(total_posts / posts_per_page)
    pad_width = max(2, len(str(total_parts)))
    base_stem, ext = os.path.splitext(os.path.basename(abs_path))

    # Strip existing -PartXX suffix if re-splitting
    clean_stem = re.sub(r'-Part\d+$', '', base_stem, flags=re.IGNORECASE)

    # Prepare part filenames: Part 1 retains the base .html filename; parts 2+ get -Part02.html, etc.
    part_filenames = [
        f"{clean_stem}{ext}" if p == 1 else f"{clean_stem}-Part{p:0{pad_width}d}{ext}"
        for p in range(1, total_parts + 1)
    ]

    # Extract or synthesize the modification log / last modified date footer
    mod_log_block = existing_mod_log or extract_or_build_modification_log(html_content, file_path=abs_path)

    print(f"  [SPLITTING] {os.path.basename(abs_path)}: {total_posts:,} posts -> {total_parts} parts ({posts_per_page:,} posts/page)")

    generated_files: List[str] = []

    for part_idx, out_filename in enumerate(part_filenames, start=1):
        start_idx = (part_idx - 1) * posts_per_page
        end_idx = min(part_idx * posts_per_page, total_posts)
        part_posts = posts[start_idx:end_idx]

        prev_fn = part_filenames[part_idx - 2] if part_idx > 1 else None
        next_fn = part_filenames[part_idx] if part_idx < total_parts else None

        # Build pagination nav
        pagination_nav = build_pagination_nav(
            prev_filename=prev_fn,
            next_filename=next_fn,
            current_part=part_idx,
            total_parts=total_parts,
            post_start=start_idx + 1,
            post_end=end_idx,
            total_posts=total_posts,
        )

        # Update headers with part badge
        part_header = update_page_titles(header_html, part_idx, total_parts)

        # Assemble document:
        # header_html (includes <ul class="messageList">)
        # + part posts
        # + modification log entry (footer with last modified date)
        # + pagination navigation (before or after </ul>)
        # + footer_html (includes </ul> closing and page footer)
        posts_body = "\n".join(part_posts)

        # Append modification log before closing </ul> inside messageList
        if mod_log_block:
            posts_body = f"{posts_body}\n\n{mod_log_block}"

        # Place pagination nav right after messageList (or right before closing </ul>)
        full_part_html = (
            f"{part_header}\n"
            f"{posts_body}\n"
            f"</ul>\n"
            f"{pagination_nav}\n"
        )
        # Append rest of footer_html (stripping any duplicate opening </ul> if present)
        clean_footer = re.sub(r'^\s*</ul>', '', footer_html, flags=re.IGNORECASE).lstrip()
        full_part_html += clean_footer

        out_path = os.path.join(target_dir, out_filename)
        generated_files.append(out_path)

        if not dry_run:
            with open(out_path, "w", encoding="utf-8") as out_fp:
                out_fp.write(full_part_html)
            size_kb = os.path.getsize(out_path) / 1024
            print(f"    [CREATED] {out_filename} ({len(part_posts):,} posts, {size_kb:.1f} KB)")
        else:
            print(f"    [DRY-RUN] Would create {out_filename} ({len(part_posts):,} posts)")

    return {
        "file": file_path,
        "status": "split",
        "posts": total_posts,
        "parts": total_parts,
        "generated_files": generated_files,
    }


def split_directory(
    directory: str,
    output_dir: Optional[str] = None,
    posts_per_page: int = DEFAULT_POSTS_PER_PAGE,
    dry_run: bool = False,
    recursive: bool = False,
) -> Dict[str, object]:
    """
    Scans a directory for HTML files and splits those exceeding posts_per_page.
    """
    target_dir = os.path.abspath(directory)
    if not os.path.isdir(target_dir):
        print(f"Error: Directory not found: {target_dir}")
        return {"scanned": 0, "split": 0, "skipped": 0, "total_parts_created": 0}

    html_files: List[str] = []
    if recursive:
        for root, _, files in os.walk(target_dir):
            for f in files:
                if f.lower().endswith(".html") and not re.search(r'-Part\d+\.html$', f, re.IGNORECASE):
                    html_files.append(os.path.join(root, f))
    else:
        for f in os.listdir(target_dir):
            if f.lower().endswith(".html") and not re.search(r'-Part\d+\.html$', f, re.IGNORECASE):
                html_files.append(os.path.join(target_dir, f))

    html_files.sort()
    scanned_count = len(html_files)
    split_count = 0
    skipped_count = 0
    total_parts_created = 0

    for fpath in html_files:
        res = split_html_file(
            file_path=fpath,
            output_dir=output_dir,
            posts_per_page=posts_per_page,
            dry_run=dry_run,
        )
        if res["status"] == "split":
            split_count += 1
            total_parts_created += res["parts"]
        else:
            skipped_count += 1

    return {
        "scanned": scanned_count,
        "split": split_count,
        "skipped": skipped_count,
        "total_parts_created": total_parts_created,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Split large WoltLab forum thread HTML documents into multi-part files with pagination."
    )
    parser.add_argument(
        "input_target",
        nargs="?",
        default=None,
        help="Path to an HTML file or a directory containing HTML files to split",
    )
    parser.add_argument(
        "--input",
        "-i",
        dest="input_opt",
        help="Path to an HTML file or a directory to split (alternative to positional argument)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        dest="output_dir",
        default=None,
        help="Output directory for generated part files (default: same as input file directory)",
    )
    parser.add_argument(
        "--posts",
        "-n",
        dest="posts_per_page",
        type=int,
        default=DEFAULT_POSTS_PER_PAGE,
        help=f"Number of posts per split file (default: {DEFAULT_POSTS_PER_PAGE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview files that would be created without writing to disk",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recursively scan subdirectories if input is a directory",
    )

    args = parser.parse_args()
    target = args.input_opt or args.input_target

    if not target:
        parser.print_help()
        sys.exit(1)

    target_path = os.path.abspath(target)
    print(f"========================================================")
    print(f"Philaforum Thread Page Splitter")
    print(f"Target:             {target_path}")
    print(f"Posts Per Page (N): {args.posts_per_page}")
    print(f"Mode:               {'DRY-RUN (Preview Only)' if args.dry_run else 'ACTIVE (Generating files)'}")
    print(f"========================================================")

    if os.path.isfile(target_path):
        res = split_html_file(
            file_path=target_path,
            output_dir=args.output_dir,
            posts_per_page=args.posts_per_page,
            dry_run=args.dry_run,
        )
        print(f"\nResult:")
        print(f"  Status:         {res['status'].upper()}")
        print(f"  Original Posts: {res.get('posts', 0):,}")
        print(f"  Parts Created:  {res.get('parts', 1)}")
    elif os.path.isdir(target_path):
        summary = split_directory(
            directory=target_path,
            output_dir=args.output_dir,
            posts_per_page=args.posts_per_page,
            dry_run=args.dry_run,
            recursive=args.recursive,
        )
        print(f"\nSummary:")
        print(f"  Files Scanned:       {summary['scanned']}")
        print(f"  Files Split:         {summary['split']}")
        print(f"  Files Skipped:       {summary['skipped']}")
        print(f"  Total Parts Created: {summary['total_parts_created']}")
    else:
        print(f"Error: Input target not found: {target_path}")
        sys.exit(1)

    print(f"========================================================")


if __name__ == "__main__":
    main()
