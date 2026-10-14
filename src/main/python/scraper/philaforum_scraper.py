#!/usr/bin/env python3
"""
Philaforum Forum PDF Scraper
Crawls forum boards and threads on philaforum.com (WoltLab Suite),
sanitizes HTML content, and generates crisp PDF files using headless Chrome/Edge.
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from typing import List, NamedTuple, Optional, Tuple
import urllib.request
import urllib.error

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

DEFAULT_BOARD_URL = "https://philaforum.com/forum/board/54-deutsches-reich-1872-1945/"
LAST_UPDATED_FILENAME = "last-updated.json"


class ThreadInfo(NamedTuple):
    url: str
    title: str
    date_str: Optional[str] = None
    dt: Optional[datetime] = None
    timestamp: float = 0.0
    is_sticky: bool = False


def parse_iso_datetime(date_str: str) -> datetime:
    """
    Parses ISO-8601 strings, UTC 'Z' notation, or date-only strings (e.g. '2016-07-01')
    into a timezone-aware datetime object in UTC.
    """
    date_str = date_str.strip()
    if date_str.endswith("Z"):
        date_str = date_str[:-1] + "+00:00"
    if " " in date_str and "T" not in date_str:
        date_str = date_str.replace(" ", "T")
    dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_last_updated(output_dir: str) -> Optional[datetime]:
    """
    Loads the last-updated date from last-updated.json in output_dir.
    Returns a timezone-aware datetime or None if not found or unparseable.
    """
    path = os.path.join(output_dir, LAST_UPDATED_FILENAME)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for key in ["last_updated", "date", "date_time", "timestamp"]:
                if key in data and data[key] is not None:
                    if key == "timestamp":
                        return datetime.fromtimestamp(float(data[key]), tz=timezone.utc)
                    return parse_iso_datetime(str(data[key]))
        elif isinstance(data, str):
            return parse_iso_datetime(data)
    except Exception as e:
        print(f"Warning: Could not read {path}: {e}")
    return None


def save_last_updated(
    output_dir: str,
    dt: datetime,
    thread_url: Optional[str] = None,
    thread_title: Optional[str] = None,
) -> None:
    """
    Saves last-updated.json to output_dir with ISO timestamp and thread metadata.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, LAST_UPDATED_FILENAME)
    payload = {
        "last_updated": dt.isoformat(),
        "timestamp": dt.timestamp(),
        "thread_url": thread_url,
        "thread_title": thread_title,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Recorded latest update in {path}: {dt.isoformat()} ({thread_title or thread_url})")


def find_browser_executable(custom_path: Optional[str] = None) -> str:
    """
    Locates a working Google Chrome or Microsoft Edge executable on Windows/Linux/macOS.
    """
    if custom_path and os.path.isfile(custom_path):
        return os.path.abspath(custom_path)

    candidate_paths = [
        # Google Chrome on Windows
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        # Microsoft Edge on Windows
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]

    for candidate in candidate_paths:
        if candidate and os.path.isfile(candidate):
            return os.path.abspath(candidate)

    # Search PATH
    for name in ["chrome", "google-chrome", "chromium", "msedge", "edge"]:
        path = shutil.which(name)
        if path:
            return os.path.abspath(path)

    raise FileNotFoundError(
        "Could not find a Google Chrome or Microsoft Edge executable. "
        "Please provide one explicitly via --browser-path."
    )


def fetch_url(url: str, timeout: int = 30) -> str:
    """
    Fetches the content of a URL using standard urllib with browser headers.
    """
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        return raw.decode("utf-8", errors="replace")


def extract_pagination_count(html_content: str) -> int:
    """
    Extracts the total page count from WoltLab <woltlab-core-pagination count="..."> element.
    Returns 1 if no pagination is found.
    """
    match = re.search(r'<woltlab-core-pagination[^>]*\bcount="(\d+)"', html_content, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 1


def extract_threads_from_board(html_content: str) -> List[ThreadInfo]:
    """
    Extracts thread items from a WoltLab board page, including URLs, titles,
    and last-updated timestamps. Returns a deduplicated list of ThreadInfo namedtuples.
    """
    threads = []
    seen = set()

    # WoltLab thread list rows
    blocks = re.findall(
        r'<ol\s+id="thread\d+"[^>]*class="[^"]*messageGroup[^"]*"[^>]*>(.*?)</ol>',
        html_content,
        re.DOTALL | re.IGNORECASE,
    )
    if not blocks:
        # Fallback for alternative or tabularListRow layouts
        blocks = re.findall(
            r'<li[^>]*class="[^"]*tabularListRow[^"]*"[^>]*>(.*?)</li>\s*(?=<li[^>]*class="[^"]*tabularListRow|<ol|</ul>|\Z)',
            html_content,
            re.DOTALL | re.IGNORECASE,
        )

    link_pattern = re.compile(
        r'<a\s+[^>]*href="([^"]*forum/thread/(\d+)(?:-[^"/?]+)?/?)[^"]*"[^>]*class="[^"]*messageGroupLink[^"]*"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    date_pattern = re.compile(r'<woltlab-core-date-time[^>]*\bdate="([^"]+)"', re.IGNORECASE)

    # If no blocks found at all, fallback to direct link searching
    if not blocks:
        for match in link_pattern.finditer(html_content):
            raw_url, raw_title = match.group(1), match.group(3)
            clean_title = html.unescape(re.sub(r"<[^>]+>", "", raw_title).strip())
            if not raw_url.startswith("http"):
                raw_url = "https://philaforum.com" + (raw_url if raw_url.startswith("/") else "/" + raw_url)
            clean_url = raw_url.split("?")[0].rstrip("/") + "/"
            if clean_url not in seen:
                seen.add(clean_url)
                threads.append(ThreadInfo(url=clean_url, title=clean_title))
        return threads

    for block in blocks:
        link_m = link_pattern.search(block)
        if not link_m:
            continue
        raw_url = link_m.group(1)
        raw_title = link_m.group(3)

        clean_title = html.unescape(re.sub(r"<[^>]+>", "", raw_title).strip())
        if not raw_url.startswith("http"):
            if raw_url.startswith("/"):
                raw_url = "https://philaforum.com" + raw_url
            else:
                raw_url = "https://philaforum.com/" + raw_url
        clean_url = raw_url.split("?")[0].rstrip("/") + "/"

        if clean_url in seen:
            continue
        seen.add(clean_url)

        is_sticky = 'data-is-sticky="1"' in block or "sticky" in block.lower()

        dates = date_pattern.findall(block)
        last_date_str = dates[-1] if dates else None
        dt = None
        ts = 0.0
        if last_date_str:
            try:
                dt = parse_iso_datetime(last_date_str)
                ts = dt.timestamp()
            except Exception:
                pass

        threads.append(
            ThreadInfo(
                url=clean_url,
                title=clean_title,
                date_str=last_date_str,
                dt=dt,
                timestamp=ts,
                is_sticky=is_sticky,
            )
        )

    return threads


def sanitize_thread_html(html_content: str, base_url: str = "https://philaforum.com/") -> str:
    """
    Sanitizes WoltLab forum thread HTML for high-quality printing:
    - Injects <base href="..."> so images and assets resolve.
    - Upgrades thumbnail images (?thumbnail=1) to original full-resolution files.
    - Injects print-specific CSS that hides forum chrome (headers, footers, sidebars, reply box).
    - Prevents ugly page breaks across individual posts and images.
    """
    # 1. Base URL tag for relative asset resolution
    if "<head>" in html_content:
        html_content = html_content.replace("<head>", f'<head><base href="{base_url}">', 1)
    elif "<HEAD>" in html_content:
        html_content = html_content.replace("<HEAD>", f'<HEAD><base href="{base_url}">', 1)

    # 2. Upgrade thumbnails to original high-res attachments
    html_content = re.sub(r'(\/attachment\/\d+-[^"\'>\s]+)\?thumbnail=1', r"\1", html_content)

    # 3. Print CSS styling, layout fluidity overrides & clutter suppression
    print_styles = """
    <style id="scraper-print-stylesheet">
    @media screen, print {
        :root {
            --wcfLayoutMinWidth: 0px !important;
            --wcfLayoutMaxWidth: 100% !important;
        }
        html, body {
            width: 100% !important;
            max-width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        /* Override WoltLab fixed layout boundaries (which default to 1000px min-width) */
        .layoutBoundary, #main, .main {
            min-width: 0 !important;
            max-width: 100% !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        /* Remove artificial margin deductions for absent right sidebar */
        .content, .content.content--sidebar-right, .sidebar + .content {
            flex: 1 1 100% !important;
            flex-basis: 100% !important;
            max-width: 100% !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        /* Fluid post structure: user sidebar on left, content expanding cleanly */
        .message {
            display: flex !important;
            flex-direction: row !important;
            width: 100% !important;
            max-width: 100% !important;
            box-sizing: border-box !important;
        }
        .messageSidebar {
            flex: 0 0 160px !important;
            width: 160px !important;
            max-width: 160px !important;
            min-width: 120px !important;
            box-sizing: border-box !important;
        }
        .messageContent {
            flex: 1 1 auto !important;
            min-width: 0 !important;
            max-width: calc(100% - 175px) !important;
            margin-left: 15px !important;
            box-sizing: border-box !important;
            word-break: break-word !important;
            overflow-wrap: break-word !important;
        }
        .messageBody, .messageText {
            min-width: 0 !important;
            max-width: 100% !important;
            word-break: break-word !important;
            overflow-wrap: break-word !important;
        }
    }
    @media print {
        @page {
            size: A4;
            margin: 12mm 10mm 12mm 10mm;
        }
        body {
            background: #ffffff !important;
            color: #1a1a1a !important;
            font-size: 11pt;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif !important;
        }
        /* Suppress forum navigation, footers, ads, and interactive widgets */
        #pageHeaderContainer, #pageHeader, #pageFooter,
        .pageNavigation, .boxesTop, .boxesBottom, .boxesSidebarLeft, .boxesSidebarRight,
        .messageGroupOptions, .wcfPostSignature, .wcfAdLocation,
        .messageQuickReply, woltlab-core-pagination, .contentInteraction,
        .wcfCookieConsent, #topMenu, .mainMenu, .messageShareButtons,
        .breadcrumbs, .reactionType, .wcfReactions {
            display: none !important;
        }
        /* Keep thread title coupled with content */
        .contentHeader {
            page-break-after: avoid !important;
            break-after: avoid !important;
            margin-bottom: 20px !important;
        }
        /* Allow posts to flow naturally across pages to prevent blank page pushes */
        .message {
            page-break-inside: auto !important;
            break-inside: auto !important;
            margin-bottom: 24px !important;
            padding-bottom: 16px !important;
            border-bottom: 1px solid #dcdcdc !important;
        }
        /* Keep post author/header with start of post */
        .messageHeader {
            page-break-after: avoid !important;
            break-after: avoid !important;
        }
        .messageBody {
            font-size: 11pt !important;
            line-height: 1.5 !important;
        }
        .attachmentThumbnailList {
            margin-top: 15px !important;
        }
        /* Keep images, figures, quotes, and attachments intact */
        img, figure, blockquote, .attachmentThumbnail {
            max-width: 100% !important;
            height: auto !important;
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }
    }
    </style>
    """

    if "</head>" in html_content:
        html_content = html_content.replace("</head>", f"{print_styles}\n</head>", 1)
    elif "</HEAD>" in html_content:
        html_content = html_content.replace("</HEAD>", f"{print_styles}\n</HEAD>", 1)
    else:
        html_content = print_styles + html_content

    return html_content


def render_html_to_pdf(
    html_content: str,
    output_pdf_path: str,
    browser_path: str,
    temp_dir: Optional[str] = None,
) -> bool:
    """
    Renders an HTML string to a PDF file using headless Chrome or Microsoft Edge.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, dir=temp_dir, encoding="utf-8") as tmp:
        tmp.write(html_content)
        temp_html_path = os.path.abspath(tmp.name)

    abs_pdf_path = os.path.abspath(output_pdf_path)

    cmd = [
        browser_path,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={abs_pdf_path}",
        temp_html_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return os.path.isfile(abs_pdf_path) and os.path.getsize(abs_pdf_path) > 0
    finally:
        if os.path.exists(temp_html_path):
            try:
                os.remove(temp_html_path)
            except OSError:
                pass


def sanitize_filename(name: str) -> str:
    """Removes invalid filename characters."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip().replace(" ", "_")
    return clean[:80] if clean else "thread"


def scrape_thread(
    thread_url: str,
    output_dir: str,
    browser_path: str,
    first_page_only: bool = False,
    max_pages: Optional[int] = None,
    delay: float = 1.0,
    thread_title: Optional[str] = None,
) -> List[str]:
    """
    Scrapes a thread and outputs a PDF for each page.
    """
    clean_base_url = thread_url.split("?")[0].rstrip("/") + "/"
    print(f"\n--- Processing Thread: {thread_title or clean_base_url} ---")

    # Fetch page 1
    page1_url = f"{clean_base_url}?pageNo=1"
    print(f"Fetching page 1: {page1_url}")
    try:
        html_p1 = fetch_url(page1_url)
    except Exception as e:
        print(f"Error fetching {page1_url}: {e}")
        return []

    total_pages = extract_pagination_count(html_p1)
    print(f"Total pages in thread: {total_pages}")

    # Determine pages to extract
    if first_page_only:
        pages_to_scrape = [1]
        print("Note: '--first-page-only' active. Scraping only page 1.")
    elif max_pages and max_pages > 0:
        limit = min(total_pages, max_pages)
        pages_to_scrape = list(range(1, limit + 1))
        print(f"Limiting to first {limit} pages.")
    else:
        pages_to_scrape = list(range(1, total_pages + 1))

    # Slug for directory / filename
    slug_match = re.search(r"/thread/(\d+-[^/?]+)", clean_base_url)
    slug = slug_match.group(1) if slug_match else sanitize_filename(thread_title or "thread")
    thread_dir = os.path.join(output_dir, sanitize_filename(slug))
    os.makedirs(thread_dir, exist_ok=True)

    generated_pdfs = []

    for page_no in pages_to_scrape:
        pdf_name = f"{sanitize_filename(slug)}_page_{page_no:03d}.pdf"
        pdf_path = os.path.join(thread_dir, pdf_name)

        if page_no == 1:
            page_html = html_p1
        else:
            page_url = f"{clean_base_url}?pageNo={page_no}"
            print(f"Fetching page {page_no}: {page_url}")
            try:
                page_html = fetch_url(page_url)
            except Exception as e:
                print(f"Failed to fetch page {page_no}: {e}")
                continue

        sanitized_html = sanitize_thread_html(page_html)
        print(f"Rendering PDF: {pdf_name}...")
        success = render_html_to_pdf(sanitized_html, pdf_path, browser_path)
        if success:
            file_size_kb = os.path.getsize(pdf_path) // 1024
            print(f"  [SUCCESS] Created {pdf_path} ({file_size_kb} KB)")
            generated_pdfs.append(pdf_path)
        else:
            print(f"  [FAILED] Could not render {pdf_name}")

        if delay > 0 and page_no != pages_to_scrape[-1]:
            time.sleep(delay)

    return generated_pdfs


def scrape_board(
    board_url: str,
    output_dir: str,
    browser_path: str,
    first_page_only: bool = False,
    max_threads: Optional[int] = None,
    max_pages: Optional[int] = None,
    delay: float = 1.0,
    force: bool = False,
    max_articles: Optional[int] = None,
    oldest_first: bool = False,
) -> List[str]:
    """
    Scrapes board listing pages, discovers threads, and generates PDFs.
    Supports incremental execution via last-updated.json, --force, --oldest-first, and --max-articles.
    """
    clean_board_url = board_url.split("?")[0].rstrip("/") + "/"
    print(f"Scraping board: {clean_board_url}")

    effective_limit = max_articles if max_articles is not None else max_threads

    # 1. Fetch initial board page to inspect total pages and top entry
    page1_url = f"{clean_board_url}?pageNo=1"
    try:
        board_html = fetch_url(page1_url)
    except Exception as e:
        print(f"Error fetching board {page1_url}: {e}")
        return []

    total_board_pages = extract_pagination_count(board_html)
    print(f"Board listing has {total_board_pages} pages.")

    # 2. Check last-updated.json unless --force is present
    last_updated_dt = None if force else load_last_updated(output_dir)
    cutoff_ts: Optional[float] = None
    if last_updated_dt:
        cutoff_dt = last_updated_dt - timedelta(minutes=1)
        cutoff_ts = cutoff_dt.timestamp()
        print(f"Incremental filter active: Only processing threads updated since {cutoff_dt.isoformat()} (recorded date minus 1 minute).")
    elif force:
        print("Note: '--force' specified. Ignoring last-updated.json.")

    # 3. If in normal (newest-first) mode, record the date of the top entry on main page
    page1_threads = extract_threads_from_board(board_html)
    if not oldest_first and page1_threads and page1_threads[0].dt:
        top_thread = page1_threads[0]
        save_last_updated(output_dir, top_thread.dt, top_thread.url, top_thread.title)

    all_generated_pdfs: List[str] = []
    articles_processed = 0

    if oldest_first:
        print(f"--- Running in --oldest-first mode (starting at page {total_board_pages} and moving backward) ---")
        curr_page = total_board_pages

        while curr_page >= 1:
            if effective_limit and articles_processed >= effective_limit:
                break

            if curr_page == 1:
                curr_html = board_html
            else:
                b_url = f"{clean_board_url}?pageNo={curr_page}"
                print(f"Crawling board page {curr_page}: {b_url}")
                try:
                    curr_html = fetch_url(b_url)
                except Exception as e:
                    print(f"Error fetching board page {curr_page}: {e}")
                    curr_page -= 1
                    continue

            page_threads = extract_threads_from_board(curr_html)
            if not page_threads:
                curr_page -= 1
                if delay > 0 and curr_page >= 1:
                    time.sleep(delay)
                continue

            # Check if all threads on this page are older than cutoff date
            if cutoff_ts is not None:
                max_ts_on_page = max((t.timestamp for t in page_threads if t.timestamp), default=0.0)
                if max_ts_on_page < cutoff_ts:
                    print(f"  Page {curr_page}: All threads are older than recorded cutoff. Skipping to page {curr_page - 1}...")
                    curr_page -= 1
                    if delay > 0 and curr_page >= 1:
                        time.sleep(delay)
                    continue
                else:
                    valid_threads = [t for t in page_threads if t.timestamp >= cutoff_ts]
            else:
                valid_threads = list(page_threads)

            # Threads on WoltLab board page are sorted newest to oldest.
            # In oldest_first mode, we reverse the page's valid threads to process the oldest first!
            valid_threads.reverse()

            print(f"  Processing {len(valid_threads)} thread(s) on page {curr_page} (oldest first)...")
            for t in valid_threads:
                if effective_limit and articles_processed >= effective_limit:
                    break
                print(f"\n[Article {articles_processed + 1}{f'/{effective_limit}' if effective_limit else ''}] Thread: {t.title} ({t.date_str or 'No date'})")
                pdfs = scrape_thread(
                    thread_url=t.url,
                    output_dir=output_dir,
                    browser_path=browser_path,
                    first_page_only=first_page_only,
                    max_pages=max_pages,
                    delay=delay,
                    thread_title=t.title,
                )
                all_generated_pdfs.extend(pdfs)
                articles_processed += 1

                # Update last-updated.json as we advance forward in time
                if t.dt:
                    save_last_updated(output_dir, t.dt, t.url, t.title)

            if first_page_only:
                break

            curr_page -= 1
            if delay > 0 and curr_page >= 1:
                time.sleep(delay)

    else:
        # Standard newest-first crawl
        if first_page_only:
            board_pages_to_crawl = [1]
            print("Note: '--first-page-only' active. Only crawling board page 1.")
        else:
            board_pages_to_crawl = list(range(1, total_board_pages + 1))

        stop_crawling = False
        for b_page in board_pages_to_crawl:
            if stop_crawling or (effective_limit and articles_processed >= effective_limit):
                break

            if b_page == 1:
                curr_html = board_html
                page_threads = page1_threads
            else:
                b_url = f"{clean_board_url}?pageNo={b_page}"
                print(f"Crawling board page {b_page}: {b_url}")
                try:
                    curr_html = fetch_url(b_url)
                except Exception as e:
                    print(f"Error fetching board page {b_page}: {e}")
                    continue
                page_threads = extract_threads_from_board(curr_html)

            print(f"  Found {len(page_threads)} threads on board page {b_page}.")

            for t in page_threads:
                if effective_limit and articles_processed >= effective_limit:
                    stop_crawling = True
                    break

                # If incremental cutoff active:
                if cutoff_ts is not None:
                    if t.timestamp and t.timestamp < cutoff_ts:
                        # If a non-sticky thread is older than cutoff, we passed the cutoff threshold
                        if not t.is_sticky:
                            print(f"  Thread '{t.title}' ({t.date_str}) is older than cutoff. Stopping incremental crawl.")
                            stop_crawling = True
                            break
                        else:
                            continue

                print(f"\n[Article {articles_processed + 1}{f'/{effective_limit}' if effective_limit else ''}] Thread: {t.title} ({t.date_str or 'No date'})")
                pdfs = scrape_thread(
                    thread_url=t.url,
                    output_dir=output_dir,
                    browser_path=browser_path,
                    first_page_only=first_page_only,
                    max_pages=max_pages,
                    delay=delay,
                    thread_title=t.title,
                )
                all_generated_pdfs.extend(pdfs)
                articles_processed += 1

            if delay > 0 and b_page != board_pages_to_crawl[-1] and not stop_crawling:
                time.sleep(delay)

    return all_generated_pdfs


def parse_arguments(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape Philaforum forum threads and generate clean PDF files using headless Chrome/Edge."
    )
    parser.add_argument(
        "--board-url",
        default=DEFAULT_BOARD_URL,
        help=f"URL of the forum board to scrape (default: {DEFAULT_BOARD_URL})",
    )
    parser.add_argument(
        "--thread-url",
        default=None,
        help="URL of a specific single thread to scrape directly (e.g. https://philaforum.com/forum/thread/9857-kleinschriftstempel/)",
    )
    parser.add_argument(
        "--first-page-only",
        action="store_true",
        help="Extract ONLY the first page (only page 1 of board and only page 1 of each thread).",
    )
    parser.add_argument(
        "--max-threads",
        type=int,
        default=None,
        help="Maximum number of threads to process across the board (alias for --max-articles).",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=None,
        help="Maximum number of articles/threads to retrieve across the board (e.g. 10).",
    )
    parser.add_argument(
        "--oldest-first",
        action="store_true",
        help="Start at the last board page and process articles backward (oldest first). Resumes from last-updated.json if present.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore last-updated.json and process threads unconditionally.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of pages to process per thread.",
    )
    parser.add_argument(
        "--output-dir",
        default="./output_pdfs",
        help="Directory to save the generated PDF files (default: ./output_pdfs)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Politeness delay in seconds between HTTP requests (default: 1.5)",
    )
    parser.add_argument(
        "--browser-path",
        default=None,
        help="Explicit path to Chrome or Edge executable. Auto-detected if omitted.",
    )
    return parser.parse_args(argv)


def main():
    args = parse_arguments()

    try:
        browser_path = find_browser_executable(args.browser_path)
        print(f"Using browser: {browser_path}")
    except FileNotFoundError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    start_time = time.time()

    if args.thread_url:
        print(f"Single thread mode: {args.thread_url}")
        pdfs = scrape_thread(
            thread_url=args.thread_url,
            output_dir=args.output_dir,
            browser_path=browser_path,
            first_page_only=args.first_page_only,
            max_pages=args.max_pages,
            delay=args.delay,
        )
    else:
        pdfs = scrape_board(
            board_url=args.board_url,
            output_dir=args.output_dir,
            browser_path=browser_path,
            first_page_only=args.first_page_only,
            max_threads=args.max_threads,
            max_pages=args.max_pages,
            delay=args.delay,
            force=args.force,
            max_articles=args.max_articles,
            oldest_first=args.oldest_first,
        )

    elapsed = time.time() - start_time
    print(f"\nFinished! Generated {len(pdfs)} PDF(s) in {elapsed:.1f}s.")
    print(f"PDF output directory: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
