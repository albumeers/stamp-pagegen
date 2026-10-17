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
Philaforum Forum PDF Scraper
Crawls forum boards and threads on philaforum.com (WoltLab Suite),
sanitizes HTML content, and generates crisp PDF files using headless Chrome/Edge.
"""

import argparse
import base64
import gc
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import List, NamedTuple, Optional, Tuple
import urllib.request
import urllib.error
import urllib.parse
try:
    import pypdf
except ImportError:
    pypdf = None

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

class NetworkRateLimiter:
    """
    Thread-safe network rate limiter ensuring HTTP requests across concurrent
    worker threads respect a minimum interval (politeness delay).
    """

    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last_request_time = 0.0

    def wait(self):
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_request_time = time.time()


GLOBAL_RATE_LIMITER: Optional[NetworkRateLimiter] = None
_IMAGE_CACHE_LOCK = threading.Lock()

DEFAULT_BOARD_URL = "https://philaforum.com/forum/board/54-deutsches-reich-1872-1945/"
BOARDS_FILENAME = "boards.json"
LEGACY_THREADS_FILENAME = "threads.json"
LEGACY_LAST_UPDATED_FILENAME = "last-updated.json"
# Backwards compatibility alias
THREADS_FILENAME = BOARDS_FILENAME


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


def load_boards_registry(output_dir: str) -> dict:
    """
    Loads boards.json from output_dir.
    Returns a dictionary of board entries (and possibly _defaults).
    If boards.json is absent:
      - Imports threads.json if present
      - Imports last-updated.json if present
    Ensures every board entry has a 'name' field.
    """
    path = os.path.join(output_dir, BOARDS_FILENAME)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for k, v in data.items():
                        if not k.startswith("_") and isinstance(v, dict):
                            if "name" not in v or not v["name"]:
                                v["name"] = sanitize_title_slug(k)
                    return data
        except Exception as e:
            print(f"Warning: Could not read {path}: {e}")
            return {}

    # Backward compatibility with legacy threads.json
    threads_path = os.path.join(output_dir, LEGACY_THREADS_FILENAME)
    if os.path.isfile(threads_path):
        try:
            with open(threads_path, "r", encoding="utf-8") as f:
                threads_data = json.load(f)
                if isinstance(threads_data, dict):
                    migrated = {}
                    first_key = None
                    for k, v in threads_data.items():
                        if isinstance(v, dict):
                            if not k.startswith("_"):
                                if first_key is None:
                                    first_key = k
                                v.setdefault("name", sanitize_title_slug(k))
                            migrated[k] = v
                    if "_defaults" not in migrated and first_key:
                        migrated["_defaults"] = {"board": first_key}
                    return migrated
        except Exception:
            pass

    # Backward compatibility with legacy last-updated.json
    legacy_path = os.path.join(output_dir, LEGACY_LAST_UPDATED_FILENAME)
    if os.path.isfile(legacy_path):
        try:
            with open(legacy_path, "r", encoding="utf-8") as f:
                legacy_data = json.load(f)
                if isinstance(legacy_data, dict):
                    default_key = "Deutsches-Reich-1872-1945"
                    return {
                        "_defaults": {"board": default_key},
                        default_key: {
                            "name": default_key,
                            "board_id": "54",
                            "board_url": legacy_data.get("board_url", DEFAULT_BOARD_URL),
                            "last_updated": legacy_data.get("last_updated"),
                            "timestamp": legacy_data.get("timestamp", 0.0),
                            "last_thread_url": legacy_data.get("thread_url"),
                            "last_thread_title": legacy_data.get("thread_title"),
                        }
                    }
        except Exception:
            pass

    return {}


def load_threads_registry(output_dir: str) -> dict:
    """Alias for load_boards_registry for backwards compatibility."""
    return load_boards_registry(output_dir)


def save_boards_registry(output_dir: str, registry: dict) -> None:
    """
    Saves the boards.json registry in output_dir, ensuring _defaults is written first.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, BOARDS_FILENAME)
    ordered_dict = {}
    if "_defaults" in registry:
        ordered_dict["_defaults"] = registry["_defaults"]
    for k, v in registry.items():
        if k != "_defaults":
            ordered_dict[k] = v
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ordered_dict, f, indent=2, ensure_ascii=False)


def save_threads_registry(output_dir: str, registry: dict) -> None:
    """Alias for save_boards_registry for backwards compatibility."""
    save_boards_registry(output_dir, registry)


def get_default_board(registry: dict) -> Optional[str]:
    """
    Returns the default board key from registry['_defaults']['board'].
    Also falls back to legacy 'board_name' or 'name' for backwards compatibility.
    """
    defaults = registry.get("_defaults")
    if isinstance(defaults, dict):
        return defaults.get("board") or defaults.get("board_name") or defaults.get("name")
    return None


# Backwards compatibility alias
get_default_board_name = get_default_board


def set_default_board(registry: dict, board_key: str) -> None:
    """
    Sets registry['_defaults']['board'] to the given board key.
    """
    if "_defaults" not in registry or not isinstance(registry["_defaults"], dict):
        registry["_defaults"] = {}
    registry["_defaults"]["board"] = board_key
    registry["_defaults"].pop("board_name", None)


# Backwards compatibility alias
set_default_board_name = set_default_board


def find_board_entry(registry: dict, identifier: str) -> Optional[Tuple[str, dict]]:
    """
    Looks up a board in the registry by key, name, board_id, or board_url.
    Ignores metadata keys starting with '_' (e.g. '_defaults').
    Returns (key, entry_dict) or None if not found.
    """
    if not identifier:
        return None

    # 1. Exact key match (skipping private keys)
    if identifier in registry and not identifier.startswith("_") and isinstance(registry[identifier], dict):
        return (identifier, registry[identifier])

    # 2. Case-insensitive key match
    id_lower = identifier.lower().strip()
    for k, v in registry.items():
        if not k.startswith("_") and isinstance(v, dict) and k.lower().strip() == id_lower:
            return (k, v)

    # 3. Match by 'name' field (exact or case-insensitive)
    for k, v in registry.items():
        if not k.startswith("_") and isinstance(v, dict):
            name_val = str(v.get("name", "")).strip()
            if name_val and name_val.lower() == id_lower:
                return (k, v)

    # 4. Slug match (on key or 'name')
    clean_id = sanitize_title_slug(identifier).lower()
    for k, v in registry.items():
        if not k.startswith("_") and isinstance(v, dict):
            if sanitize_title_slug(k).lower() == clean_id:
                return (k, v)
            name_val = str(v.get("name", "")).strip()
            if name_val and sanitize_title_slug(name_val).lower() == clean_id:
                return (k, v)

    # 5. Match by board_id
    for k, v in registry.items():
        if not k.startswith("_") and isinstance(v, dict) and str(v.get("board_id", "")).strip() == identifier.strip():
            return (k, v)

    # 6. Match by board_url
    clean_target_url = identifier.strip().rstrip("/")
    for k, v in registry.items():
        if not k.startswith("_") and isinstance(v, dict):
            b_url = str(v.get("board_url", "")).rstrip("/")
            if b_url and (clean_target_url in b_url or b_url in clean_target_url):
                return (k, v)

    return None


def get_board_language(
    registry: Optional[dict] = None,
    board_key: Optional[str] = None,
    cli_lang: Optional[str] = None,
) -> str:
    """
    Resolves the forum locale / language code:
    1. Explicit CLI argument (--lang)
    2. Board-specific entry in boards.json ('lang' or 'locale' attribute)
    3. Global '_defaults' entry in boards.json ('lang' or 'locale' attribute)
    4. Default fallback: 'de'
    """
    if cli_lang:
        return cli_lang.strip().lower()
    if registry:
        if board_key:
            matched = find_board_entry(registry, board_key)
            if matched:
                entry = matched[1]
                lang = entry.get("lang") or entry.get("locale")
                if lang:
                    return str(lang).strip().lower()
        defaults = registry.get("_defaults", {})
        if isinstance(defaults, dict):
            lang = defaults.get("lang") or defaults.get("locale")
            if lang:
                return str(lang).strip().lower()
    return "de"


def extract_board_info_from_url(url: str) -> Tuple[str, str]:
    """
    Extracts (board_id, default_slug) from a board URL.
    Example: 'https://philaforum.com/forum/board/54-deutsches-reich-1872-1945/' -> ('54', 'Deutsches-Reich-1872-1945')
    """
    m = re.search(r'/board/(\d+)(?:-([^/?#]+))?', url)
    if m:
        board_id = m.group(1)
        raw_slug = m.group(2)
        if raw_slug:
            parts = [p.capitalize() if p.isalpha() else p for p in raw_slug.split("-")]
            slug = sanitize_title_slug("-".join(parts))
        else:
            slug = f"Board-{board_id}"
        return (board_id, slug)
    return ("", "board")


def update_board_in_registry(
    output_dir: str,
    board_key: str,
    board_id: str,
    board_url: str,
    dt: datetime,
    board_name: Optional[str] = None,
    thread_url: Optional[str] = None,
    thread_title: Optional[str] = None,
    lang: Optional[str] = None,
    pdf_file: Optional[str] = None,
) -> None:
    """
    Updates or inserts a board entry in boards.json, updates _defaults.board_name,
    and saves boards.json.
    """
    registry = load_boards_registry(output_dir)
    matched = (
        find_board_entry(registry, board_key)
        or (find_board_entry(registry, board_name) if board_name else None)
        or find_board_entry(registry, board_id)
        or find_board_entry(registry, board_url)
    )
    actual_key = matched[0] if matched else board_key

    existing_entry = registry.get(actual_key, {})
    if not isinstance(existing_entry, dict):
        existing_entry = {}

    resolved_name = (
        board_name
        or existing_entry.get("name")
        or sanitize_title_slug(actual_key)
    )

    existing_entry.update({
        "name": resolved_name,
        "board_id": board_id or existing_entry.get("board_id", ""),
        "board_url": board_url or existing_entry.get("board_url", ""),
        "last_updated": dt.isoformat(),
        "timestamp": dt.timestamp(),
        "last_thread_url": thread_url or existing_entry.get("last_thread_url"),
        "last_thread_title": thread_title or existing_entry.get("last_thread_title"),
    })
    if pdf_file:
        existing_entry["last_pdf"] = os.path.basename(pdf_file)
    if lang:
        existing_entry["lang"] = lang
    registry[actual_key] = existing_entry
    set_default_board(registry, actual_key)
    save_boards_registry(output_dir, registry)
    pdf_info = f" -> {os.path.basename(pdf_file)}" if pdf_file else ""
    print(
        f"Recorded update for board '{actual_key}' ({resolved_name}) in "
        f"{os.path.join(output_dir, BOARDS_FILENAME)}: {dt.isoformat()} ({thread_title or thread_url}){pdf_info}"
    )


def load_board_last_updated(output_dir: str, board_identifier: str) -> Optional[datetime]:
    """
    Loads last_updated date for a specific board from boards.json.
    """
    registry = load_boards_registry(output_dir)
    matched = find_board_entry(registry, board_identifier)
    if matched:
        entry = matched[1]
        for key in ["last_updated", "date", "date_time", "timestamp"]:
            if key in entry and entry[key] is not None:
                if key == "timestamp":
                    return datetime.fromtimestamp(float(entry[key]), tz=timezone.utc)
                return parse_iso_datetime(str(entry[key]))
    return None


def load_last_updated(output_dir: str, board_identifier: Optional[str] = None) -> Optional[datetime]:
    """
    Loads the last-updated date from boards.json (or legacy last-updated.json / threads.json).
    If board_identifier is given, returns that board's date; otherwise returns the newest date.
    """
    if board_identifier:
        return load_board_last_updated(output_dir, board_identifier)

    registry = load_boards_registry(output_dir)
    latest_dt: Optional[datetime] = None
    for k, entry in registry.items():
        if k.startswith("_"):
            continue
        if isinstance(entry, dict) and "last_updated" in entry and entry["last_updated"]:
            try:
                dt = parse_iso_datetime(str(entry["last_updated"]))
                if latest_dt is None or dt > latest_dt:
                    latest_dt = dt
            except Exception:
                pass
    return latest_dt


def save_last_updated(
    output_dir: str,
    dt: datetime,
    thread_url: Optional[str] = None,
    thread_title: Optional[str] = None,
    board_key: Optional[str] = None,
    board_id: Optional[str] = None,
    board_url: Optional[str] = None,
    board_name: Optional[str] = None,
) -> None:
    """
    Convenience function to record an update in boards.json.
    """
    update_board_in_registry(
        output_dir=output_dir,
        board_key=board_key or "Deutsches-Reich-1872-1945",
        board_id=board_id or "54",
        board_url=board_url or DEFAULT_BOARD_URL,
        dt=dt,
        board_name=board_name,
        thread_url=thread_url,
        thread_title=thread_title,
    )


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


COOKIE: Optional[str] = None


def parse_cookie_input(content: str) -> str:
    """
    Parses cookie input from either:
    1. Standard HTTP Cookie header string ('name1=val1; name2=val2')
    2. Netscape HTTP Cookie File format (tab-separated lines from browser export extensions)
    3. Multi-line 'name=value' format
    Returns a normalized HTTP Cookie header string ('name1=val1; name2=val2').
    """
    if not content:
        return ""
    content = content.strip()
    # Check if this is a Netscape cookie file
    if "# Netscape HTTP Cookie File" in content or "\t" in content:
        cookies = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                name = parts[5].strip()
                val = parts[6].strip()
                if name:
                    cookies.append(f"{name}={val}")
        if cookies:
            return "; ".join(cookies)
    # Check if lines have key=value pairs (one per line)
    if "\n" in content and ";" not in content:
        pairs = []
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                pairs.append(line)
        if pairs:
            return "; ".join(pairs)
    # Default: single line header format, clean up any leading 'Cookie:' prefix
    clean = re.sub(r"^Cookie:\s*", "", content, flags=re.IGNORECASE).strip()
    return clean


def fetch_url(url: str, timeout: int = 30) -> str:
    """
    Fetches the content of a URL using standard urllib with browser headers.
    Includes session cookie if configured.
    Respects GLOBAL_RATE_LIMITER if configured.
    """
    if GLOBAL_RATE_LIMITER is not None:
        GLOBAL_RATE_LIMITER.wait()

    headers = {"User-Agent": USER_AGENT, "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"}
    if COOKIE:
        headers["Cookie"] = COOKIE
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


_IMAGE_CACHE: dict = {}

GERMAN_TRANSLITERATION = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "Ä": "Ae",
    "Ö": "Oe",
    "Ü": "Ue",
    "ß": "ss",
}


def transliterate_german(text: str) -> str:
    """
    Transliterates German umlauts and eszett to standard ASCII equivalents:
    ä -> ae, ö -> oe, ü -> ue, Ä -> Ae, Ö -> Oe, Ü -> Ue, ß -> ss.
    Unquotes percent-encoded sequences (e.g. %C3%BC) before transliteration.
    """
    if not text:
        return ""
    if "%" in text:
        try:
            text = urllib.parse.unquote(text)
        except Exception:
            pass
    for orig, repl in GERMAN_TRANSLITERATION.items():
        text = text.replace(orig, repl)
    return text


def get_image_filename(url: str, mime: Optional[str] = None) -> str:
    """
    Derives a clean, safe filename for an image URL.
    Translates WoltLab attachment slugs like '/attachment/1663-1-jpg/' into '1663-1.jpg'.
    Transliterates German umlauts (ä -> ae, ö -> oe, ü -> ue, ß -> ss) and removes percent-encoding
    to ensure filenames and URLs resolve reliably across Windows filesystem and PDF viewers.
    """
    clean_url = url.split("?")[0].rstrip("/")
    if "%" in clean_url:
        try:
            clean_url = urllib.parse.unquote(clean_url)
        except Exception:
            pass

    # Check for WoltLab attachment pattern: /attachment/(\d+)(?:-([^/?#]+))?
    m = re.search(r"/attachment/(\d+)(?:-([^/?#]+))?", clean_url, re.IGNORECASE)
    if m:
        att_id = m.group(1)
        raw_name = m.group(2) or "attachment"
        raw_name = transliterate_german(raw_name)
        # WoltLab represents extensions as hyphen suffixes: -jpg, -jpeg, -png, -gif, -webp
        ext_m = re.search(r"-(jpe?g|png|gif|webp)$", raw_name, re.IGNORECASE)
        if ext_m:
            base_part = raw_name[: ext_m.start()]
            ext_part = ext_m.group(1).lower()
            base_part = re.sub(r'[\\/*?:"<>|%]', "", base_part).strip()
            return f"{att_id}-{base_part}.{ext_part}"
        elif re.search(r"\.(jpe?g|png|gif|webp)$", raw_name, re.IGNORECASE):
            raw_name = re.sub(r'[\\/*?:"<>|%]', "", raw_name).strip()
            return f"{att_id}-{raw_name}"
        else:
            ext = ".jpg"
            if mime:
                if "png" in mime.lower():
                    ext = ".png"
                elif "gif" in mime.lower():
                    ext = ".gif"
                elif "webp" in mime.lower():
                    ext = ".webp"
            raw_name = re.sub(r'[\\/*?:"<>|%]', "", raw_name).strip()
            return f"{att_id}-{raw_name}{ext}"

    # General image URL
    parsed = urllib.parse.urlparse(clean_url)
    base = os.path.basename(parsed.path)
    base = transliterate_german(base)
    clean_base = re.sub(r'[\\/*?:"<>|%]', "", base).strip()
    if clean_base and "." in clean_base:
        return clean_base

    # Fallback with mime or hash
    ext = ".jpg"
    if mime:
        if "png" in mime.lower():
            ext = ".png"
        elif "gif" in mime.lower():
            ext = ".gif"
        elif "webp" in mime.lower():
            ext = ".webp"
    stem = clean_base if clean_base else f"img_{abs(hash(clean_url)) % 100000}"
    return f"{stem}{ext}"


def fetch_and_save_image(
    url: str,
    base_url: str = "https://philaforum.com/",
    images_dir: Optional[str] = None,
    image_link_prefix: str = "../images/",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Downloads an image, embeds it as a base64 data URI, and optionally saves it
    to images_dir, returning (data_uri, file_uri).
    If the file already exists on disk in images_dir, loads it directly from disk.
    Caches results in _IMAGE_CACHE.
    """
    if not url or url.startswith("data:"):
        return (url, None)

    full_url = urllib.parse.urljoin(base_url, url)
    full_url = re.sub(r'(\/attachment\/\d+[^"\'>\s]*)\?thumbnail=1', r"\1", full_url)

    with _IMAGE_CACHE_LOCK:
        if full_url in _IMAGE_CACHE:
            cached_data, cached_file = _IMAGE_CACHE[full_url]
            if cached_file or not images_dir:
                return (cached_data, cached_file)

    # If images_dir is specified and file already exists, load directly from disk
    if images_dir:
        provisional_name = get_image_filename(full_url)
        candidate_path = os.path.join(images_dir, provisional_name)
        # Fallback check for already downloaded image under legacy ID or raw name
        if not (os.path.isfile(candidate_path) and os.path.getsize(candidate_path) > 0):
            m_att = re.search(r"/attachment/(\d+)", full_url, re.IGNORECASE)
            if m_att and os.path.isdir(images_dir):
                att_prefix = f"{m_att.group(1)}-"
                try:
                    for f in os.listdir(images_dir):
                        if f.startswith(att_prefix):
                            candidate_path = os.path.join(images_dir, f)
                            provisional_name = f
                            break
                except Exception:
                    pass

        if os.path.isfile(candidate_path) and os.path.getsize(candidate_path) > 0:
            try:
                with open(candidate_path, "rb") as f:
                    raw = f.read()
                ext = os.path.splitext(candidate_path)[1].lower().lstrip(".")
                mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"
                b64 = base64.b64encode(raw).decode("ascii")
                data_uri = f"data:{mime};base64,{b64}"
                prefix = image_link_prefix.rstrip("/")
                file_uri = f"{prefix}/{provisional_name}"
                with _IMAGE_CACHE_LOCK:
                    _IMAGE_CACHE[full_url] = (data_uri, file_uri)
                return (data_uri, file_uri)
            except Exception:
                pass

    if GLOBAL_RATE_LIMITER is not None:
        GLOBAL_RATE_LIMITER.wait()

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    if COOKIE:
        headers["Cookie"] = COOKIE
    req = urllib.request.Request(full_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            mime = resp.headers.get_content_type() or "image/jpeg"
            b64 = base64.b64encode(raw).decode("ascii")
            data_uri = f"data:{mime};base64,{b64}"

            file_uri = None
            if images_dir:
                os.makedirs(images_dir, exist_ok=True)
                fname = get_image_filename(full_url, mime)
                local_path = os.path.join(images_dir, fname)
                with _IMAGE_CACHE_LOCK:
                    if not (os.path.isfile(local_path) and os.path.getsize(local_path) > 0):
                        with open(local_path, "wb") as f:
                            f.write(raw)
                prefix = image_link_prefix.rstrip("/")
                file_uri = f"{prefix}/{fname}"

            with _IMAGE_CACHE_LOCK:
                _IMAGE_CACHE[full_url] = (data_uri, file_uri)
            return (data_uri, file_uri)
    except Exception:
        return (None, None)


def fetch_image_data_uri(url: str, base_url: str = "https://philaforum.com/") -> Optional[str]:
    """
    Downloads an image and converts it into a base64 data URI.
    Backwards-compatible wrapper around fetch_and_save_image.
    """
    data_uri, _ = fetch_and_save_image(url, base_url=base_url)
    return data_uri


def is_decorative_image(url: str, attrs: str = "") -> bool:
    """
    Returns True if an image is an emoji, smiley, icon, logo, or avatar.
    Such images are embedded as Base64 for offline rendering, but should not be saved
    as standalone image files or made into clickable links.
    """
    low_url = (url or "").lower()
    low_attrs = (attrs or "").lower()
    return (
        any(k in low_url for k in ["/smilies/", "/smiley/", "/emojis/", "/emoji/", "/avatars/", "/avatar/", "pagelogo"])
        or any(k in low_attrs for k in ["smiley", "wcemoji", "useravatarimage"])
    )


def embed_and_link_images(
    html_content: str,
    base_url: str = "https://philaforum.com/",
    images_dir: Optional[str] = None,
    image_link_prefix: str = "../images/",
) -> str:
    """
    Replaces <img> src attributes with inline base64 data URIs so PDFs are completely
    self-contained and independent of the live website.
    Downloads and saves images to images_dir (if provided), and rewrites image anchor tags
    so that clicking an image in the PDF opens the local image file (e.g. ../images/) instead of
    external website URLs.
    If local file saving fails or is not enabled, neutralizes image anchor tags into spans.
    Also strips thumbnail query parameters (?thumbnail=1) and hardcoded thumbnail dimensions
    (width/height) so full-resolution images render crisply.
    """
    # 1. Upgrade thumbnails to original full-resolution attachments
    html_content = re.sub(r'(\/attachment\/\d+[^"\'>\s]*)\?thumbnail=1', r"\1", html_content)

    # 2. First pass: Handle anchors wrapping images
    # We use a non-greedy negative lookahead regex to match single <a>...</a> blocks without swallowing
    # preceding or subsequent <a> tags.
    anchor_pattern = re.compile(
        r'<a\b([^>]*)>((?:(?!</?a\b).)*?<img\b[^>]*>(?:(?!</?a\b).)*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    def process_anchor_match(m):
        attrs = m.group(1)
        inner = m.group(2)

        href_m = re.search(r'\bhref=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
        src_m = re.search(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\']', inner, re.IGNORECASE)

        orig_href = href_m.group(1) if href_m else ""
        orig_src = src_m.group(1) if src_m else ""

        # Determine target image URL: prefer href if it looks like an image or attachment, else src
        target_img_url = orig_src
        if orig_href and ("attachment" in orig_href or re.search(r"\.(jpe?g|png|gif|webp)", orig_href, re.IGNORECASE)):
            target_img_url = orig_href

        is_decorative = is_decorative_image(target_img_url, attrs)
        data_uri, file_uri = None, None
        if target_img_url:
            data_uri, file_uri = fetch_and_save_image(
                target_img_url, base_url, None if is_decorative else images_dir, image_link_prefix=image_link_prefix
            )

        if not data_uri and orig_src and orig_src != target_img_url:
            data_uri, file_uri_src = fetch_and_save_image(
                orig_src, base_url, None if is_decorative else images_dir, image_link_prefix=image_link_prefix
            )
            if not file_uri:
                file_uri = file_uri_src

        # Replace <img> src in inner with data_uri (or keep original if download failed)
        new_inner = inner
        if data_uri:
            new_inner = re.sub(
                r'(<img\b[^>]*\bsrc=["\'])[^"\']*(["\'])',
                rf"\g<1>{data_uri}\2",
                new_inner,
                count=1,
                flags=re.IGNORECASE,
            )
        # Strip hardcoded width and height attributes from <img> so it scales naturally
        new_inner = re.sub(r'\s*\b(width|height)=["\']\d+["\']', "", new_inner, flags=re.IGNORECASE)

        # Rewrite anchor or neutralize
        if file_uri and not is_decorative:
            clean_attrs = re.sub(r'\s*\bhref=["\'][^"\']*["\']', "", attrs, flags=re.IGNORECASE).strip()
            clean_attrs = re.sub(r'\s*\btarget=["\'][^"\']*["\']', "", clean_attrs, flags=re.IGNORECASE).strip()
            clean_attrs = re.sub(r"\bjsImageViewer\b", "", clean_attrs).strip()
            attr_str = f" {clean_attrs}" if clean_attrs else ""
            return f'<a href="{file_uri}"{attr_str} target="_blank" title="Click to open local image">{new_inner}</a>'
        else:
            clean_attrs = re.sub(r'\s*\bhref=["\'][^"\']*["\']', "", attrs, flags=re.IGNORECASE).strip()
            clean_attrs = re.sub(r"\bjsImageViewer\b", "", clean_attrs).strip()
            attr_str = f" {clean_attrs}" if clean_attrs else ""
            return f"<span{attr_str}>{new_inner}</span>"

    html_content = anchor_pattern.sub(process_anchor_match, html_content)

    # 3. Second pass: Process any standalone <img> tags not inside <a> tags
    img_pattern = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)

    def process_standalone_img(m):
        full_tag = m.group(0)
        attrs = m.group(1)

        src_m = re.search(r'\bsrc=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
        if not src_m:
            return full_tag
        src = src_m.group(1)
        if src.startswith("data:"):
            return full_tag  # Already embedded

        is_decorative = is_decorative_image(src, attrs)
        data_uri, file_uri = fetch_and_save_image(
            src, base_url, None if is_decorative else images_dir, image_link_prefix=image_link_prefix
        )
        new_tag = full_tag
        if data_uri:
            new_tag = re.sub(
                r'(\bsrc=["\'])[^"\']*(["\'])',
                rf"\g<1>{data_uri}\2",
                new_tag,
                count=1,
                flags=re.IGNORECASE,
            )
        new_tag = re.sub(r'\s*\b(width|height)=["\']\d+["\']', "", new_tag, flags=re.IGNORECASE)

        if file_uri and not is_decorative:
            return f'<a href="{file_uri}" target="_blank" title="Click to open local image">{new_tag}</a>'
        return new_tag

    html_content = img_pattern.sub(process_standalone_img, html_content)

    # 4. Fourth pass: Process attachment file cards (messageAttachment without <img>)
    attachment_card_pattern = re.compile(
        r'<a\b([^>]*\bhref=["\']([^"\']*\/attachment\/\d+[^"\']*)["\'][^>]*)>((?:(?!</?a\b).)*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    def process_attachment_card(m):
        full_attrs = m.group(1)
        href_val = m.group(2)
        inner = m.group(3)

        # Skip if already converted to local file or contains <img>
        if "<img" in inner.lower() or "file:///" in full_attrs or "../images/" in full_attrs:
            return m.group(0)

        # Check if this card represents an image file (by filename extension or icon)
        is_image_attachment = bool(
            re.search(r'[-.](jpe?g|png|gif|webp)(?:/|$|\b)', href_val, re.IGNORECASE)
            or re.search(r'\.(jpe?g|png|gif|webp)\b', inner, re.IGNORECASE)
            or "file-image" in inner.lower()
        )

        if not is_image_attachment:
            return m.group(0)

        data_uri, file_uri = fetch_and_save_image(href_val, base_url, images_dir, image_link_prefix=image_link_prefix)

        if data_uri and file_uri:
            # Successfully downloaded image: inject image preview directly into the card
            clean_attrs = re.sub(r'\s*\bhref=["\'][^"\']*["\']', '', full_attrs, flags=re.IGNORECASE).strip()
            clean_attrs = re.sub(r'\s*\btarget=["\'][^"\']*["\']', '', clean_attrs, flags=re.IGNORECASE).strip()
            clean_attrs = re.sub(r'\bjsTooltip\b', '', clean_attrs).strip()
            attr_str = f" {clean_attrs}" if clean_attrs else ""
            img_tag = (
                f'<div class="attachmentImagePreview" style="margin-bottom:8px;">'
                f'<img class="embeddedImage" src="{data_uri}" style="max-width:100%;max-height:850px;object-fit:contain;display:block;margin:0 auto;">'
                f'</div>'
            )
            return f'<a href="{file_uri}"{attr_str} target="_blank" title="Click to open local image">{img_tag}{inner}</a>'
        else:
            # Download failed (e.g. 403 Forbidden guest access)
            # Neutralize href so clicking the box in the PDF does not open the remote URL unexpectedly
            clean_attrs = re.sub(r'\s*\bhref=["\'][^"\']*["\']', '', full_attrs, flags=re.IGNORECASE).strip()
            clean_attrs = re.sub(r'\bjsTooltip\b', '', clean_attrs).strip()
            attr_str = f" {clean_attrs}" if clean_attrs else ""
            return f'<span{attr_str} title="Protected attachment (Login required)">{inner}</span>'

    html_content = attachment_card_pattern.sub(process_attachment_card, html_content)

    return html_content


def embed_images_in_html(html_content: str, base_url: str = "https://philaforum.com/") -> str:
    """
    Backwards compatibility wrapper around embed_and_link_images.
    """
    return embed_and_link_images(html_content, base_url=base_url, images_dir=None)


def neutralize_image_anchors(html_content: str) -> str:
    """
    Converts <a> tags enclosing images into inert <span> elements by removing the href attribute,
    ensuring that clicking images inside the PDF does not open forum URLs.
    Preserves local file:/// links if present.
    Uses safe non-greedy lookahead regex to avoid swallowing preceding anchors.
    """
    pattern = re.compile(
        r'<a\b([^>]*)>((?:(?!</?a\b).)*?(?:<img\b|<picture\b|<figure\b)(?:(?!</?a\b).)*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    def repl(m):
        attrs = m.group(1)
        inner = m.group(2)
        if re.search(r'\bhref=["\'](?:file:|\.\./images/|images/)', attrs, re.IGNORECASE):
            return m.group(0)
        clean_attrs = re.sub(r'\s*\bhref=["\'][^"\']*["\']', "", attrs, flags=re.IGNORECASE).strip()
        attr_str = f" {clean_attrs}" if clean_attrs else ""
        return f"<span{attr_str}>{inner}</span>"

    return pattern.sub(repl, html_content)


def sanitize_thread_html(
    html_content: str,
    base_url: str = "https://philaforum.com/",
    images_dir: Optional[str] = None,
    image_link_prefix: str = "../images/",
) -> str:
    """
    Sanitizes WoltLab forum thread HTML for high-quality printing:
    - Embeds images as inline base64 data URIs for offline independence.
    - Saves local image files into images_dir and rewrites image anchor links to point to local relative URIs (../images/...).
    - Neutralizes any remote hyperlinks wrapping images into spans so external URLs are never opened.
    - Injects print-specific CSS that hides forum chrome and renders clean page numbers.
    - Prevents ugly page breaks across individual posts and images.
    """
    # 1. Strip any <base href="..."> tags so relative paths (like '../images/...') resolve against the local filesystem
    html_content = re.sub(r"<base\b[^>]*>", "", html_content, flags=re.IGNORECASE)

    # 2. Embed images directly as base64 data URIs and link to local relative image URIs
    html_content = embed_and_link_images(html_content, base_url, images_dir, image_link_prefix=image_link_prefix)

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
        /* De-emphasize user details: hide avatar and scale down sidebar to 0.65 */
        .userAvatar {
            display: none !important;
        }
        .messageSidebar {
            flex: 0 0 130px !important;
            width: 130px !important;
            max-width: 130px !important;
            min-width: 80px !important;
            transform: scale(0.65) !important;
            transform-origin: top left !important;
            box-sizing: border-box !important;
        }
        @media screen and (min-width: 1025px), print {
            .messageSidebar + .messageContent {
                flex-basis: calc(100% - 160px) !important;
                margin-left: 30px !important;
                max-width: calc(100% - 160px) !important;
            }
        }
        .messageContent {
            flex: 1 1 auto !important;
            min-width: 0 !important;
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
            margin: 12mm 10mm 15mm 10mm;
            @bottom-right {
                content: counter(page) " / " counter(pages);
                font-size: 8pt;
                color: #666666;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            }
            @bottom-left {
                content: "";
            }
        }
        body {
            background: #ffffff !important;
            color: #1a1a1a !important;
            font-size: 11pt;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif !important;
        }
        /* Suppress forum navigation, footers, ads, user avatar, and interactive widgets */
        #pageHeaderContainer, #pageHeader, #pageFooter,
        .pageNavigation, .boxesTop, .boxesBottom, .boxesSidebarLeft, .boxesSidebarRight,
        .messageGroupOptions, .wcfPostSignature, .wcfAdLocation,
        .messageQuickReply, woltlab-core-pagination, .contentInteraction,
        .wcfCookieConsent, #topMenu, .mainMenu, .messageShareButtons,
        .breadcrumbs, .reactionType, .wcfReactions, .userAvatar {
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
        /* Expand WoltLab attachment cards and previews to full width so images are not squeezed by CSS Grid */
        .messageAttachmentList {
            display: block !important;
            grid-template-columns: none !important;
        }
        .messageAttachment {
            display: block !important;
            grid-template-columns: none !important;
            grid-template-areas: none !important;
            max-width: 100% !important;
            width: auto !important;
        }
        .attachmentImagePreview {
            display: block !important;
            width: 100% !important;
            max-width: 100% !important;
            text-align: center !important;
            margin-bottom: 12px !important;
        }
        .embeddedImage, .attachmentThumbnail img, .attachmentImagePreview img, .messageAttachment img, .messageBody img, .messageText img {
            max-width: 100% !important;
            max-height: 850px !important;
            object-fit: contain !important;
            height: auto !important;
            display: inline-block !important;
        }
        a[href^="file:"] {
            text-decoration: none !important;
            cursor: pointer !important;
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
    timeout: Optional[int] = None,
) -> bool:
    """
    Renders an HTML string to a PDF file using headless Chrome or Microsoft Edge.
    Suppresses browser-generated headers/footers (--no-pdf-header-footer) so file:// URLs are not printed.
    Uses an adaptive rendering timeout (minimum 300s) to comfortably render large multi-page threads.
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
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={abs_pdf_path}",
        temp_html_path,
    ]

    if timeout is not None and timeout > 0:
        effective_timeout = timeout
    else:
        # Adaptive timeout based on document size:
        # Minimum 300 seconds (5 min), plus 30s per MB of HTML content.
        size_mb = len(html_content) / (1024 * 1024)
        effective_timeout = max(300, int(300 + size_mb * 30))

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=effective_timeout)
        if res.returncode != 0:
            print(f"Warning: Browser returned exit code {res.returncode}: {res.stderr[:300]}")
        return os.path.isfile(abs_pdf_path) and os.path.getsize(abs_pdf_path) > 0
    except subprocess.TimeoutExpired:
        print(
            f"Warning: Browser rendering timed out after {effective_timeout}s for "
            f"'{os.path.basename(output_pdf_path)}' (HTML size: {len(html_content) // 1024} KB). "
            f"Try increasing --render-timeout."
        )
        return False
    except Exception as e:
        print(f"Warning: Error during PDF rendering: {e}")
        return False
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


def sanitize_title_slug(text: str) -> str:
    """
    Sanitizes thread title or slug for directory and PDF filenames.
    Keeps caps as defined, replaces ' ' with '-', strips leading numeric ID prefixes,
    and normalizes Unicode dashes (en-dash, em-dash) to standard ASCII hyphens.
    Example: 'Dienstbrief aus 1941' -> 'Dienstbrief-aus-1941'
    Example: '54-deutsches-reich-1872-1945' -> 'Deutsches-Reich-1872-1945'
    Example: 'Deutsches Reich 1872–1945' -> 'Deutsches-Reich-1872-1945'
    """
    if not text:
        return "thread"
    # Remove leading numeric ID prefix like '1174-' if present
    clean = re.sub(r"^\d+-", "", text.strip())
    # Normalize unicode dashes (en-dash \u2013, em-dash \u2014, figure dash, minus) to regular hyphen
    clean = re.sub(r"[\u2010-\u2015\u2212]", "-", clean)
    # Remove invalid filesystem characters
    clean = re.sub(r'[\\/*?:"<>|]', "", clean)
    # Replace spaces with hyphens
    clean = re.sub(r"\s+", "-", clean)
    # Ensure leading character is uppercase if it was lowercase, preserving internal casing
    if clean and clean[0].islower():
        clean = clean[0].upper() + clean[1:]
    # Collapse multiple hyphens
    clean = re.sub(r"-+", "-", clean)
    clean = clean.strip("- .")
    return clean[:100] if clean else "thread"


def find_tag_bounds(html_text: str, tag_name: str, class_pattern: str) -> Optional[Tuple[int, int, int, int]]:
    """
    Finds (start_tag_start, start_tag_end, closing_tag_start, closing_tag_end)
    properly accounting for nested tags of the same type.
    """
    pattern = rf'<{tag_name}\b[^>]*class="[^"]*{class_pattern}[^"]*"[^>]*>'
    start_match = re.search(pattern, html_text, re.IGNORECASE)
    if not start_match:
        return None

    start_pos = start_match.start()
    content_start = start_match.end()

    depth = 1
    token_pattern = re.compile(rf'(<{tag_name}\b[^>]*>)|(</{tag_name}\s*>)', re.IGNORECASE)
    for m in token_pattern.finditer(html_text, content_start):
        if m.group(1):
            depth += 1
        elif m.group(2):
            depth -= 1
            if depth == 0:
                return (start_pos, content_start, m.start(), m.end())
    return None


def extract_thread_posts(html_content: str) -> str:
    """
    Extracts the inner HTML of the thread's messageList container,
    handling nested tags properly.
    """
    bounds = find_tag_bounds(html_content, "ul", "messageList")
    if bounds:
        return html_content[bounds[1]:bounds[2]].strip()

    # Fallback: extract all <article ... class="...message..."> elements
    articles = re.findall(
        r'<article\b[^>]*class="[^"]*message[^"]*"[^>]*>.*?</article>',
        html_content,
        re.DOTALL | re.IGNORECASE,
    )
    if articles:
        return "\n".join(articles)
    return ""


def combine_thread_pages(base_html: str, additional_pages_html: List[str]) -> str:
    """
    Combines posts from additional thread pages into the base page's messageList container.
    """
    if not additional_pages_html:
        return base_html

    collected_posts = [p for page in additional_pages_html if (p := extract_thread_posts(page))]
    if not collected_posts:
        return base_html

    combined_posts_str = "\n".join(collected_posts)
    base_bounds = find_tag_bounds(base_html, "ul", "messageList")
    if base_bounds:
        return (
            base_html[: base_bounds[2]]
            + "\n<!-- Additional Forum Page Posts Appended -->\n"
            + combined_posts_str
            + "\n"
            + base_html[base_bounds[2] :]
        )

    # Fallback if base_html lacks messageList container: append before </main>, </section>, or </body>
    for closing_tag in ["</main>", "</section>", "</body>"]:
        pos = base_html.lower().rfind(closing_tag)
        if pos != -1:
            return (
                base_html[:pos]
                + "\n<!-- Additional Forum Page Posts Appended -->\n"
                + combined_posts_str
                + "\n"
                + base_html[pos:]
            )

    return base_html + "\n" + combined_posts_str


def get_pdf_page_count(pdf_path: str) -> int:
    """
    Returns the total number of pages in the given PDF file.
    Uses pypdf if available, falling back to scanning PDF /Type /Page tokens.
    """
    if not os.path.isfile(pdf_path):
        return 0
    if pypdf is not None:
        try:
            reader = pypdf.PdfReader(pdf_path)
            return len(reader.pages)
        except Exception:
            pass
    try:
        with open(pdf_path, "rb") as f:
            data = f.read()
        matches = re.findall(rb"/Type\s*/Page\b", data)
        return len(matches)
    except Exception:
        return 0


def split_message_list_posts(inner_content: str) -> List[str]:
    """
    Splits the inner HTML of a thread message list into individual top-level post HTML chunks.
    Properly handles nested lists (<ul>/<ol>/<li>) and diverse post wrappers.
    """
    if not inner_content or not inner_content.strip():
        return []

    # Check for top-level <li> elements
    li_matches = list(re.finditer(r"<li\b[^>]*>", inner_content, re.IGNORECASE))
    if li_matches:
        posts: List[str] = []
        token_pattern = re.compile(r"(<li\b[^>]*>)|(</li>)", re.IGNORECASE)

        current_post_start = None
        depth = 0

        for m in token_pattern.finditer(inner_content):
            if m.group(1):  # <li ...>
                if depth == 0:
                    current_post_start = m.start()
                    depth = 1
                else:
                    tag_str = m.group(1)
                    # If an unclosed <li> happened, detect top-level post boundary
                    if re.search(r'\b(?:id=["\']post\d+["\']|class=["\'][^"\']*(?:wbbPost|tabularListRow))', tag_str, re.IGNORECASE):
                        if current_post_start is not None:
                            posts.append(inner_content[current_post_start:m.start()].strip())
                        current_post_start = m.start()
                        depth = 1
                    else:
                        depth += 1
            elif m.group(2):  # </li>
                if depth > 0:
                    depth -= 1
                    if depth == 0 and current_post_start is not None:
                        posts.append(inner_content[current_post_start:m.end()].strip())
                        current_post_start = None

        if current_post_start is not None and current_post_start < len(inner_content):
            trailing = inner_content[current_post_start:].strip()
            if trailing:
                posts.append(trailing)

        filtered = [p for p in posts if p.strip()]
        if filtered:
            return filtered

    # Fallback: check for <article class="...message..."> elements
    article_matches = list(
        re.finditer(
            r'<article\b[^>]*class="[^"]*message[^"]*"[^>]*>.*?</article>',
            inner_content,
            re.DOTALL | re.IGNORECASE,
        )
    )
    if article_matches:
        return [m.group(0).strip() for m in article_matches if m.group(0).strip()]

    return [inner_content.strip()]


def split_thread_posts(html_content: str) -> Tuple[str, List[str], str]:
    """
    Extracts the header HTML before the thread posts, a list of individual post HTML
    strings, and the footer HTML following the posts.
    """
    bounds = find_tag_bounds(html_content, "ul", "messageList")
    if bounds:
        header_html = html_content[:bounds[1]]
        inner_content = html_content[bounds[1]:bounds[2]]
        footer_html = html_content[bounds[2]:]
        posts = split_message_list_posts(inner_content)
        return header_html, posts, footer_html

    # Fallback: search for <article class="...message..."> elements
    article_matches = list(
        re.finditer(
            r'<article\b[^>]*class="[^"]*message[^"]*"[^>]*>.*?</article>',
            html_content,
            re.DOTALL | re.IGNORECASE,
        )
    )
    if article_matches:
        header_html = html_content[:article_matches[0].start()]
        posts = [m.group(0).strip() for m in article_matches]
        footer_html = html_content[article_matches[-1].end():]
        return header_html, posts, footer_html

    return html_content, [], ""


def assemble_part_html(
    header_html: str,
    posts: List[str],
    footer_html: str,
    next_pdf_filename: Optional[str] = None,
    prev_pdf_filename: Optional[str] = None,
    part_index: int = 1,
) -> str:
    """
    Assembles a complete HTML document for a specific part of a multi-part thread,
    inserting navigation banners and continuation links when appropriate.
    """
    items = []
    is_in_ul = "<ul" in header_html.lower() and "</ul" in footer_html.lower()

    # Navigation banner for Part 2 and beyond
    if prev_pdf_filename:
        prev_inner = (
            f'<div class="prevPartLink" style="background-color: #f8f9fa; border: 1px solid #c0d0e0; border-radius: 6px; padding: 10px 18px; font-size: 11pt; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Arial, sans-serif; color: #333333;">'
            f'<span><strong>Teil {part_index} / Part {part_index}</strong> &bull; Vorheriger Teil / Previous part: '
            f'<a href="{prev_pdf_filename}" style="color: #0066cc; text-decoration: underline; font-weight: bold;">{prev_pdf_filename}</a></span>'
            f'</div>'
        )
        if is_in_ul:
            prev_banner = f'<li class="prevPartLinkListItem" style="list-style: none !important; width: 100% !important; margin: 10px 0 25px 0; padding: 0 !important;">{prev_inner}</li>'
        else:
            prev_banner = f'<div class="prevPartLinkContainer" style="width: 100% !important; margin: 10px 0 25px 0; padding: 0 !important;">{prev_inner}</div>'
        items.append(prev_banner)

    items.extend(posts)

    # Continuation link banner to next part
    if next_pdf_filename:
        next_inner = (
            f'<div class="nextPartLink" style="background-color: #f0f4f8; border: 1px solid #b8d0e8; border-radius: 6px; padding: 14px 20px; font-size: 12pt; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Arial, sans-serif; text-align: center; color: #1a1a1a;">'
            f'<strong>Fortsetzung in / Continued in:</strong> '
            f'<a href="{next_pdf_filename}" style="color: #0066cc; text-decoration: underline; font-weight: bold;">{next_pdf_filename}</a>'
            f'</div>'
        )
        if is_in_ul:
            next_banner = f'<li class="nextPartLinkListItem" style="list-style: none !important; width: 100% !important; margin: 35px 0 20px 0; padding: 0 !important; page-break-before: avoid !important;">{next_inner}</li>'
        else:
            next_banner = f'<div class="nextPartLinkContainer" style="width: 100% !important; margin: 35px 0 20px 0; padding: 0 !important; page-break-before: avoid !important;">{next_inner}</div>'
        items.append(next_banner)

    return header_html + "\n" + "\n".join(items) + "\n" + footer_html


def scrape_thread(
    thread_url: str,
    output_dir: str,
    browser_path: str,
    first_page_only: bool = False,
    max_pages: Optional[int] = None,
    delay: float = 1.0,
    thread_title: Optional[str] = None,
    board_dir: Optional[str] = None,
    render_timeout: Optional[int] = None,
    lang: str = "de",
    max_pdf_pages: int = 50,
) -> List[str]:
    """
    Scrapes a thread, combining all pages into a single seamless PDF.
    If the rendered PDF exceeds max_pdf_pages (default 50), it splits the thread into
    multi-part PDFs at whole post boundaries with continuation links.
    If board_dir is provided, saves images directly inside board_dir/images/
    and PDFs inside board_dir/<lang>/.
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

    # Determine clean text title for folder and PDF naming
    if not thread_title:
        title_m = re.search(r'<h1[^>]*class="[^"]*contentTitle[^"]*"[^>]*>(.*?)</h1>', html_p1, re.DOTALL | re.IGNORECASE)
        if title_m:
            clean_t = html.unescape(re.sub(r'<[^>]+>', '', title_m.group(1)).strip())
            if clean_t:
                thread_title = clean_t
        if not thread_title:
            slug_m = re.search(r'/thread/([^/?]+)', clean_base_url)
            thread_title = slug_m.group(1) if slug_m else "thread"

    title_slug = sanitize_title_slug(thread_title)
    base_dir = board_dir if board_dir else output_dir
    os.makedirs(base_dir, exist_ok=True)
    images_dir = os.path.join(base_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    pdf_dir = os.path.join(base_dir, lang)
    os.makedirs(pdf_dir, exist_ok=True)

    generated_pdfs: List[str] = []

    # Fetch any additional pages beyond page 1
    additional_pages_html: List[str] = []
    for page_no in pages_to_scrape[1:]:
        page_url = f"{clean_base_url}?pageNo={page_no}"
        print(f"Fetching page {page_no}: {page_url}")
        try:
            page_html = fetch_url(page_url)
            additional_pages_html.append(page_html)
        except Exception as e:
            print(f"Failed to fetch page {page_no}: {e}")

        if delay > 0 and page_no != pages_to_scrape[-1]:
            time.sleep(delay)

    # Combine all pages into a single document if there are multiple pages
    if additional_pages_html:
        combined_html = combine_thread_pages(html_p1, additional_pages_html)
        print(f"Combined {1 + len(additional_pages_html)} forum pages into a single thread document.")
    else:
        combined_html = html_p1

    sanitized_html = sanitize_thread_html(combined_html, base_url=clean_base_url, images_dir=images_dir, image_link_prefix="../images/")
    pdf_name = f"{title_slug}.pdf"
    pdf_path = os.path.join(pdf_dir, pdf_name)

    print(f"Rendering PDF: {pdf_name}...")
    success = render_html_to_pdf(sanitized_html, pdf_path, browser_path, temp_dir=pdf_dir, timeout=render_timeout)
    if not success:
        print(f"  [FAILED] Could not render {pdf_name}")
        return generated_pdfs

    rendered_page_count = get_pdf_page_count(pdf_path)

    # If within limit (or splitting disabled), return the single PDF
    if max_pdf_pages <= 0 or rendered_page_count <= max_pdf_pages:
        file_size_kb = os.path.getsize(pdf_path) // 1024
        print(f"  [SUCCESS] Created {pdf_path} ({file_size_kb} KB, {rendered_page_count} pages)")
        generated_pdfs.append(pdf_path)
        return generated_pdfs

    # Thread exceeded max_pdf_pages: split into multi-part PDFs at post boundaries
    header_html, posts, footer_html = split_thread_posts(sanitized_html)
    if len(posts) <= 1:
        # Cannot break across a single post
        file_size_kb = os.path.getsize(pdf_path) // 1024
        print(f"  [SUCCESS] Created {pdf_path} ({file_size_kb} KB, {rendered_page_count} pages, single unsplit post)")
        generated_pdfs.append(pdf_path)
        return generated_pdfs

    print(
        f"  Thread exceeded limit ({rendered_page_count} pages > {max_pdf_pages} max). "
        f"Splitting {len(posts)} posts into multi-part PDFs at post boundaries..."
    )

    # Remove the oversized unsplit initial render
    try:
        os.remove(pdf_path)
    except OSError:
        pass

    part_index = 1
    remaining_posts = list(posts)
    prev_pdf_filename: Optional[str] = None

    try:
        while remaining_posts:
            part_name = f"{title_slug}.pdf" if part_index == 1 else f"{title_slug}-Part{part_index}.pdf"
            part_path = os.path.join(pdf_dir, part_name)

            # If only 1 post remaining, it must go in this part
            if len(remaining_posts) == 1:
                part_html = assemble_part_html(
                    header_html,
                    remaining_posts[:1],
                    footer_html,
                    next_pdf_filename=None,
                    prev_pdf_filename=prev_pdf_filename,
                    part_index=part_index,
                )
                print(f"  Rendering Part {part_index}: {part_name} (1 final post)...")
                ok = render_html_to_pdf(part_html, part_path, browser_path, temp_dir=pdf_dir, timeout=render_timeout)
                if ok:
                    p_count = get_pdf_page_count(part_path)
                    kb = os.path.getsize(part_path) // 1024
                    print(f"  [SUCCESS] Created {part_path} ({kb} KB, {p_count} pages)")
                    generated_pdfs.append(part_path)
                else:
                    print(f"  [FAILED] Could not render {part_name}")
                break

            # Test if all remaining posts fit into <= max_pdf_pages
            test_all_html = assemble_part_html(
                header_html,
                remaining_posts,
                footer_html,
                next_pdf_filename=None,
                prev_pdf_filename=prev_pdf_filename,
                part_index=part_index,
            )
            test_all_pdf = os.path.join(pdf_dir, f".tmp_all_part_{part_index}_{os.getpid()}.pdf")
            test_all_ok = render_html_to_pdf(test_all_html, test_all_pdf, browser_path, temp_dir=pdf_dir, timeout=render_timeout)
            if test_all_ok:
                all_pages = get_pdf_page_count(test_all_pdf)
                if all_pages <= max_pdf_pages:
                    if os.path.exists(part_path):
                        try:
                            os.remove(part_path)
                        except OSError:
                            pass
                    shutil.move(test_all_pdf, part_path)
                    kb = os.path.getsize(part_path) // 1024
                    print(f"  [SUCCESS] Created final {part_path} ({kb} KB, {all_pages} pages, {len(remaining_posts)} posts)")
                    generated_pdfs.append(part_path)
                    break
                else:
                    if os.path.exists(test_all_pdf):
                        try:
                            os.remove(test_all_pdf)
                        except OSError:
                            pass
            else:
                if os.path.exists(test_all_pdf):
                    try:
                        os.remove(test_all_pdf)
                    except OSError:
                        pass

            # Remaining posts require further partitioning: establish link to next part
            next_pdf_filename = f"{title_slug}-Part{part_index + 1}.pdf"

            # Binary search to find maximum posts fitting in <= max_pdf_pages
            low = 1
            high = len(remaining_posts) - 1
            best_k = 1
            best_temp_path: Optional[str] = None

            total_rem_chars = sum(len(p) for p in remaining_posts)
            if rendered_page_count > 0 and total_rem_chars > 0:
                target_chars = total_rem_chars * (max_pdf_pages / rendered_page_count)
                cur_c = 0
                k_est = 1
                for idx, p in enumerate(remaining_posts):
                    cur_c += len(p)
                    if cur_c >= target_chars:
                        k_est = max(1, min(high, idx + 1))
                        break
            else:
                k_est = (low + high) // 2

            first_test = True

            while low <= high:
                if first_test and low <= k_est <= high:
                    mid = k_est
                    first_test = False
                else:
                    mid = (low + high) // 2
                    first_test = False

                candidate_html = assemble_part_html(
                    header_html,
                    remaining_posts[:mid],
                    footer_html,
                    next_pdf_filename=next_pdf_filename,
                    prev_pdf_filename=prev_pdf_filename,
                    part_index=part_index,
                )
                temp_cand_pdf = os.path.join(pdf_dir, f".tmp_cand_{part_index}_{mid}_{os.getpid()}.pdf")
                cand_ok = render_html_to_pdf(candidate_html, temp_cand_pdf, browser_path, temp_dir=pdf_dir, timeout=render_timeout)

                if cand_ok:
                    c_pages = get_pdf_page_count(temp_cand_pdf)
                    if c_pages <= max_pdf_pages:
                        best_k = mid
                        if best_temp_path and os.path.exists(best_temp_path):
                            try:
                                os.remove(best_temp_path)
                            except OSError:
                                pass
                        best_temp_path = os.path.join(pdf_dir, f".best_part_{part_index}_{os.getpid()}.pdf")
                        shutil.move(temp_cand_pdf, best_temp_path)
                        low = mid + 1
                    else:
                        if os.path.exists(temp_cand_pdf):
                            try:
                                os.remove(temp_cand_pdf)
                            except OSError:
                                pass
                        high = mid - 1
                else:
                    if os.path.exists(temp_cand_pdf):
                        try:
                            os.remove(temp_cand_pdf)
                        except OSError:
                            pass
                    high = mid - 1

            # Finalize Part
            if best_temp_path and os.path.exists(best_temp_path):
                if os.path.exists(part_path):
                    try:
                        os.remove(part_path)
                    except OSError:
                        pass
                shutil.move(best_temp_path, part_path)
                p_count = get_pdf_page_count(part_path)
                kb = os.path.getsize(part_path) // 1024
                print(f"  [SUCCESS] Created {part_path} ({kb} KB, {p_count} pages, {best_k} posts)")
                generated_pdfs.append(part_path)
            else:
                # Even single post exceeded max_pdf_pages; render post 1 alone
                best_k = 1
                single_post_html = assemble_part_html(
                    header_html,
                    remaining_posts[:1],
                    footer_html,
                    next_pdf_filename=next_pdf_filename,
                    prev_pdf_filename=prev_pdf_filename,
                    part_index=part_index,
                )
                ok = render_html_to_pdf(single_post_html, part_path, browser_path, temp_dir=pdf_dir, timeout=render_timeout)
                if ok:
                    p_count = get_pdf_page_count(part_path)
                    kb = os.path.getsize(part_path) // 1024
                    print(f"  [SUCCESS] Created {part_path} ({kb} KB, {p_count} pages, single oversized post)")
                    generated_pdfs.append(part_path)
                else:
                    print(f"  [FAILED] Could not render {part_name}")
                    break

            remaining_posts = remaining_posts[best_k:]
            prev_pdf_filename = part_name
            part_index += 1
    finally:
        # Clean up any leftover temporary search files
        for f in os.listdir(pdf_dir):
            if f.startswith((".tmp_cand_", ".tmp_all_", ".best_part_")):
                try:
                    os.remove(os.path.join(pdf_dir, f))
                except OSError:
                    pass

    return generated_pdfs


def scrape_board(
    board_url: str,
    output_dir: str,
    browser_path: str,
    board_key: Optional[str] = None,
    first_page_only: bool = False,
    max_threads: Optional[int] = None,
    max_pages: Optional[int] = None,
    delay: float = 1.0,
    force: bool = False,
    max_articles: Optional[int] = None,
    oldest_first: bool = False,
    render_timeout: Optional[int] = None,
    lang: Optional[str] = None,
    workers: int = 1,
    max_pdf_pages: int = 50,
) -> List[str]:
    """
    Scrapes board listing pages, discovers threads, and generates PDFs directly into a board folder.
    Supports incremental execution via threads.json, --force, --oldest-first, and --max-articles.
    When workers > 1, threads on each board page are scraped and rendered in parallel.
    """
    global GLOBAL_RATE_LIMITER
    GLOBAL_RATE_LIMITER = NetworkRateLimiter(min_interval=delay)
    workers = max(1, workers)

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

    board_id, default_slug = extract_board_info_from_url(clean_board_url)
    registry = load_boards_registry(output_dir)

    matched = None
    if board_key:
        matched = find_board_entry(registry, board_key)
    if not matched:
        matched = find_board_entry(registry, clean_board_url) or find_board_entry(registry, board_id)

    if matched:
        board_key, entry = matched
        folder_name = entry.get("name") or sanitize_title_slug(board_key)
    else:
        title_m = re.search(r'<h1[^>]*class="[^"]*contentTitle[^"]*"[^>]*>(.*?)</h1>', board_html, re.DOTALL | re.IGNORECASE)
        board_title = None
        if title_m:
            clean_t = html.unescape(re.sub(r'<[^>]+>', '', title_m.group(1)).strip())
            if clean_t:
                board_title = clean_t
        folder_name = sanitize_title_slug(board_title or default_slug)
        if not board_key:
            board_key = folder_name

    board_dir = os.path.join(output_dir, folder_name)
    os.makedirs(board_dir, exist_ok=True)
    board_lang = get_board_language(registry, board_key, cli_lang=lang)
    print(f"Board output folder: {board_dir} (locale: {board_lang})")

    # 2. Check boards.json unless --force is present
    last_updated_dt = None if force else load_board_last_updated(output_dir, board_key)
    cutoff_ts: Optional[float] = None
    if last_updated_dt:
        cutoff_dt = last_updated_dt - timedelta(minutes=1)
        cutoff_ts = cutoff_dt.timestamp()
        print(f"Incremental filter active: Only processing threads updated since {cutoff_dt.isoformat()} (recorded date minus 1 minute).")
    elif force:
        print(f"Note: '--force' specified. Ignoring {BOARDS_FILENAME}.")

    # 3. Fast Page 1 cutoff check: If incremental filter is active, check if the newest
    # thread on the entire board (page 1) is already older than the cutoff.
    # If so, nothing on the board has changed and we can exit immediately without crawling.
    page1_threads = extract_threads_from_board(board_html)
    if cutoff_ts is not None and page1_threads:
        non_sticky = [t for t in page1_threads if not t.is_sticky and t.timestamp]
        newest_board_ts = max((t.timestamp for t in (non_sticky or page1_threads)), default=0.0)
        if newest_board_ts > 0 and newest_board_ts < cutoff_ts:
            newest_dt_str = datetime.fromtimestamp(newest_board_ts, tz=timezone.utc).isoformat()
            print(
                f"Board is already up-to-date. Newest thread on page 1 ({newest_dt_str}) "
                f"is older than recorded cutoff ({cutoff_dt.isoformat()}). Nothing to scrape."
            )
            return []

    # In normal (newest-first) mode, track whether the top thread timestamp has been recorded
    # once its document is successfully written to disk
    recorded_newest_first_top = False

    all_generated_pdfs: List[str] = []
    articles_processed = 0
    cached_board_pages: dict = {1: board_html}

    def _process_single_thread(t: ThreadInfo) -> Tuple[ThreadInfo, List[str]]:
        res_pdfs = scrape_thread(
            thread_url=t.url,
            output_dir=output_dir,
            browser_path=browser_path,
            first_page_only=first_page_only,
            max_pages=max_pages,
            delay=delay,
            thread_title=t.title,
            board_dir=board_dir,
            render_timeout=render_timeout,
            lang=board_lang,
            max_pdf_pages=max_pdf_pages,
        )
        return t, res_pdfs

    def _process_threads_batch(threads: List[ThreadInfo]) -> None:
        nonlocal articles_processed, recorded_newest_first_top
        if not threads:
            return
        if workers > 1 and len(threads) > 1:
            pool_size = min(workers, len(threads))
            print(f"  Dispatching {len(threads)} thread(s) across {pool_size} worker(s)...")
            with ThreadPoolExecutor(max_workers=pool_size) as executor:
                futures = [executor.submit(_process_single_thread, t) for t in threads]
                for fut in futures:
                    t, res_pdfs = fut.result()
                    articles_processed += 1
                    print(f"  [Article {articles_processed}{f'/{effective_limit}' if effective_limit else ''} Completed] {t.title}")
                    all_generated_pdfs.extend(res_pdfs)
                    if res_pdfs:
                        # Record update to boards.json ONLY after document was successfully generated & written
                        if oldest_first and t.dt:
                            update_board_in_registry(
                                output_dir=output_dir,
                                board_key=board_key,
                                board_id=board_id,
                                board_url=clean_board_url,
                                dt=t.dt,
                                board_name=folder_name,
                                thread_url=t.url,
                                thread_title=t.title,
                                pdf_file=res_pdfs[0],
                                lang=board_lang,
                            )
                        elif not oldest_first and not recorded_newest_first_top and page1_threads and page1_threads[0].dt:
                            top_thread = page1_threads[0]
                            update_board_in_registry(
                                output_dir=output_dir,
                                board_key=board_key,
                                board_id=board_id,
                                board_url=clean_board_url,
                                dt=top_thread.dt,
                                board_name=folder_name,
                                thread_url=top_thread.url,
                                thread_title=top_thread.title,
                                pdf_file=res_pdfs[0],
                                lang=board_lang,
                            )
                            recorded_newest_first_top = True
        else:
            for t in threads:
                articles_processed += 1
                print(f"\n[Article {articles_processed}{f'/{effective_limit}' if effective_limit else ''}] Thread: {t.title} ({t.date_str or 'No date'})")
                t, res_pdfs = _process_single_thread(t)
                all_generated_pdfs.extend(res_pdfs)
                if res_pdfs:
                    # Record update to boards.json ONLY after document was successfully generated & written
                    if oldest_first and t.dt:
                        update_board_in_registry(
                            output_dir=output_dir,
                            board_key=board_key,
                            board_id=board_id,
                            board_url=clean_board_url,
                            dt=t.dt,
                            board_name=folder_name,
                            thread_url=t.url,
                            thread_title=t.title,
                            pdf_file=res_pdfs[0],
                            lang=board_lang,
                        )
                    elif not oldest_first and not recorded_newest_first_top and page1_threads and page1_threads[0].dt:
                        top_thread = page1_threads[0]
                        update_board_in_registry(
                            output_dir=output_dir,
                            board_key=board_key,
                            board_id=board_id,
                            board_url=clean_board_url,
                            dt=top_thread.dt,
                            board_name=folder_name,
                            thread_url=top_thread.url,
                            thread_title=top_thread.title,
                            pdf_file=res_pdfs[0],
                            lang=board_lang,
                        )
                        recorded_newest_first_top = True

    if oldest_first:
        print(f"--- Running in --oldest-first mode (starting at page {total_board_pages} and moving backward) ---")
        curr_page = total_board_pages

        # Fast page search: If cutoff is active, binary search to find the oldest page containing updates
        if cutoff_ts is not None and total_board_pages > 1:
            print(f"Locating starting page for cutoff {cutoff_dt.isoformat()} across {total_board_pages} pages...")
            last_url = f"{clean_board_url}?pageNo={total_board_pages}"
            try:
                last_html = fetch_url(last_url)
                cached_board_pages[total_board_pages] = last_html
                last_threads = extract_threads_from_board(last_html)
                last_max_ts = max((t.timestamp for t in last_threads if t.timestamp), default=0.0)
            except Exception as e:
                print(f"Warning: Could not fetch last page {total_board_pages}: {e}")
                last_max_ts = 0.0

            if last_max_ts >= cutoff_ts:
                curr_page = total_board_pages
            else:
                low = 1
                high = total_board_pages - 1
                while low < high:
                    mid = (low + high + 1) // 2
                    mid_url = f"{clean_board_url}?pageNo={mid}"
                    try:
                        mid_html = fetch_url(mid_url)
                        cached_board_pages[mid] = mid_html
                        mid_threads = extract_threads_from_board(mid_html)
                        mid_max_ts = max((t.timestamp for t in mid_threads if t.timestamp), default=0.0)
                    except Exception as e:
                        print(f"Warning during page search on page {mid}: {e}")
                        mid_max_ts = 0.0

                    if mid_max_ts >= cutoff_ts:
                        low = mid
                    else:
                        high = mid - 1

                curr_page = low
                print(f"Fast-forwarded: Starting crawl at page {curr_page} (oldest page containing threads >= cutoff).")

        while curr_page >= 1:
            if effective_limit and articles_processed >= effective_limit:
                break

            if curr_page in cached_board_pages:
                curr_html = cached_board_pages.pop(curr_page)
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

            remaining = (effective_limit - articles_processed) if effective_limit else len(valid_threads)
            threads_to_process = valid_threads[:remaining]
            print(f"  Processing {len(threads_to_process)} thread(s) on page {curr_page} (oldest first)...")
            _process_threads_batch(threads_to_process)

            with _IMAGE_CACHE_LOCK:
                _IMAGE_CACHE.clear()
            gc.collect()

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

            threads_to_process: List[ThreadInfo] = []
            for t in page_threads:
                if effective_limit and (articles_processed + len(threads_to_process)) >= effective_limit:
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

                threads_to_process.append(t)

            _process_threads_batch(threads_to_process)

            with _IMAGE_CACHE_LOCK:
                _IMAGE_CACHE.clear()
            gc.collect()

            if delay > 0 and b_page != board_pages_to_crawl[-1] and not stop_crawling:
                time.sleep(delay)

    with _IMAGE_CACHE_LOCK:
        _IMAGE_CACHE.clear()
    gc.collect()

    return all_generated_pdfs


def parse_arguments(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape Philaforum forum threads and generate clean PDF files using headless Chrome/Edge."
    )
    parser.add_argument(
        "--board",
        default=None,
        help="Name or key of the board in boards.json to scrape (e.g. 'Deutsches-Reich-1872-1945', 'dr', or '54').",
    )
    parser.add_argument(
        "--board-url",
        default=None,
        help="URL of the forum board to scrape (e.g. https://philaforum.com/forum/board/54-deutsches-reich-1872-1945/).",
    )
    parser.add_argument(
        "--thread-url",
        default=None,
        help="URL of a specific single thread to scrape directly (e.g. https://philaforum.com/forum/thread/9857-kleinschriftstempel/).",
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
        help="Start at the last board page and process articles backward (oldest first). Resumes from boards.json if present.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore boards.json and process threads unconditionally.",
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
        help="Directory to save the generated PDF files and boards.json (default: ./output_pdfs)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Politeness delay in seconds between HTTP requests (default: 1.5)",
    )
    parser.add_argument(
        "--cookie",
        default=None,
        help="Session cookie string to authenticate requests with the forum (e.g. 'wsc30_user_session=...; XSRF-TOKEN=...').",
    )
    parser.add_argument(
        "--cookie-file",
        default=None,
        help="Path to a text file containing the session cookie string.",
    )
    parser.add_argument(
        "--browser-path",
        default=None,
        help="Explicit path to Chrome or Edge executable. Auto-detected if omitted.",
    )
    parser.add_argument(
        "--render-timeout",
        type=int,
        default=None,
        help="Maximum time in seconds to wait for browser to render a PDF (default: adaptive, min 300s).",
    )
    parser.add_argument(
        "--lang",
        default=None,
        help="Locale/language subfolder for generated PDFs (e.g. 'de'). Defaults to boards.json setting or 'de'.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of concurrent worker threads for scraping and rendering threads on each board page (default: 1).",
    )
    parser.add_argument(
        "--max-pdf-pages",
        type=int,
        default=50,
        help="Maximum PDF pages per document before splitting into multi-part PDFs (default: 50; 0 to disable).",
    )
    return parser.parse_args(argv)


def main():
    args = parse_arguments()

    global COOKIE
    if args.cookie:
        COOKIE = parse_cookie_input(args.cookie)
    elif args.cookie_file and os.path.isfile(args.cookie_file):
        try:
            with open(args.cookie_file, "r", encoding="utf-8") as f:
                COOKIE = parse_cookie_input(f.read())
            print(f"Loaded session cookie from {args.cookie_file}")
        except Exception as e:
            print(f"Warning: Could not read cookie file {args.cookie_file}: {e}")

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
        GLOBAL_RATE_LIMITER = NetworkRateLimiter(min_interval=args.delay)
        pdfs = scrape_thread(
            thread_url=args.thread_url,
            output_dir=args.output_dir,
            browser_path=browser_path,
            first_page_only=args.first_page_only,
            max_pages=args.max_pages,
            delay=args.delay,
            render_timeout=args.render_timeout,
            lang=args.lang or "de",
            max_pdf_pages=args.max_pdf_pages,
        )
        with _IMAGE_CACHE_LOCK:
            _IMAGE_CACHE.clear()
        gc.collect()
    else:
        registry = load_boards_registry(args.output_dir)
        board_url = None
        board_key = None
        board_target = args.board

        # If --board and --board-url are not specified, check _defaults in boards.json
        if not board_target and not args.board_url:
            default_board = get_default_board(registry)
            if default_board:
                print(f"Using default board from {BOARDS_FILENAME}: '{default_board}'")
                board_target = default_board

        if board_target:
            matched = find_board_entry(registry, board_target)
            if not matched:
                boards_path = os.path.join(args.output_dir, BOARDS_FILENAME)
                print(
                    f"Error: Board '{board_target}' was not found in {boards_path}. "
                    "Please specify --board-url to register it first.",
                    file=sys.stderr,
                )
                sys.exit(1)
            board_key, entry = matched
            board_url = entry.get("board_url")
            if not board_url:
                print(
                    f"Error: Board entry '{board_key}' in {BOARDS_FILENAME} is missing a 'board_url'.",
                    file=sys.stderr,
                )
                sys.exit(1)
            print(f"Loaded board '{board_key}' ({entry.get('name', board_key)}) from {BOARDS_FILENAME} -> {board_url}")
            # Ensure _defaults.board points to this board_key
            set_default_board(registry, board_key)
            save_boards_registry(args.output_dir, registry)
        elif args.board_url:
            board_url = args.board_url
            matched = find_board_entry(registry, board_url)
            if matched:
                board_key = matched[0]
                set_default_board(registry, board_key)
                save_boards_registry(args.output_dir, registry)
        else:
            boards_path = os.path.join(args.output_dir, BOARDS_FILENAME)
            print(
                f"Error: Either --board-url or --board is required (no default found in {boards_path}).",
                file=sys.stderr,
            )
            sys.exit(1)

        pdfs = scrape_board(
            board_url=board_url,
            output_dir=args.output_dir,
            browser_path=browser_path,
            board_key=board_key,
            first_page_only=args.first_page_only,
            max_threads=args.max_threads,
            max_pages=args.max_pages,
            delay=args.delay,
            force=args.force,
            max_articles=args.max_articles,
            oldest_first=args.oldest_first,
            render_timeout=args.render_timeout,
            lang=args.lang,
            workers=args.workers,
            max_pdf_pages=args.max_pdf_pages,
        )

    elapsed = time.time() - start_time
    print(f"\nFinished! Generated {len(pdfs)} PDF(s) in {elapsed:.1f}s.")
    print(f"PDF output directory: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
