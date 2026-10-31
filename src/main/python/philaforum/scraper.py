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
Philaforum Pure HTML Scraper
Crawls forum boards and threads on philaforum.com (WoltLab Suite),
sanitizes HTML content into printer-friendly format, downloads attached images,
and saves German HTML articles directly to <forum-folder>/html/<title_slug>.html
with relative references to ../images/<filename>.
"""

import argparse
import base64
import html
import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, NamedTuple, Optional, Tuple
import urllib.error
import urllib.parse
import urllib.request

try:
    from .cleanup import clean_modification_log_entries, fix_blockquote_display, strip_unwanted_scripts
except (ImportError, ValueError):
    try:
        from philaforum.cleanup import clean_modification_log_entries, fix_blockquote_display, strip_unwanted_scripts
    except ImportError:
        from cleanup import clean_modification_log_entries, fix_blockquote_display, strip_unwanted_scripts

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

BOARDS_FILENAME = "boards.json"
DEFAULT_DELAY = 1.0


class NetworkRateLimiter:
    """
    Thread-safe network rate limiter ensuring HTTP requests across threads
    respect a minimum politeness delay.
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
_IMAGE_CACHE: Dict[str, Tuple[Optional[str], Optional[str]]] = {}
COOKIE: Optional[str] = None


class ThreadInfo(NamedTuple):
    url: str
    title: str
    date_str: Optional[str] = None
    dt: Optional[datetime] = None
    timestamp: float = 0.0
    is_sticky: bool = False


def parse_cookie_input(cookie_arg: str) -> Optional[str]:
    """
    Resolves cookie string or loads credentials from cookie file.
    Supports:
    1. Netscape HTTP Cookie File (standard browser export extension format)
    2. JSON cookie export ([{"name": "...", "value": "..."}, ...] or {"k": "v"})
    3. Multi-line name=value format
    4. Raw HTTP Cookie header string ('name1=val1; name2=val2')
    """
    if not cookie_arg:
        return None

    raw_text = cookie_arg
    cand_path = os.path.expandvars(os.path.expanduser(cookie_arg.strip()))
    if os.path.isfile(cand_path):
        try:
            with open(cand_path, "r", encoding="utf-8") as f:
                raw_text = f.read().strip()
        except Exception as e:
            print(f"Warning: Could not read cookie file '{cand_path}': {e}")
            return None

    if not raw_text or not raw_text.strip():
        return None

    content = raw_text.strip()

    # 1. JSON format
    if (content.startswith("[") and content.endswith("]")) or (content.startswith("{") and content.endswith("}")):
        try:
            parsed_json = json.loads(content)
            pairs = []
            if isinstance(parsed_json, list):
                for item in parsed_json:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        pairs.append(f"{item['name']}={item['value']}")
            elif isinstance(parsed_json, dict):
                for k, v in parsed_json.items():
                    pairs.append(f"{k}={v}")
            if pairs:
                return "; ".join(pairs)
        except Exception:
            pass

    # 2. Netscape HTTP Cookie File format
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

    # 3. Multi-line key=value format
    if "\n" in content and ";" not in content:
        pairs = []
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                pairs.append(line)
        if pairs:
            return "; ".join(pairs)

    # 4. Standard Cookie header or string (strip leading 'Cookie:' prefix)
    clean = re.sub(r"^Cookie:\s*", "", content, flags=re.IGNORECASE).strip()
    return clean if clean else None


def parse_iso_datetime(date_str: str) -> datetime:
    """Parses ISO-8601 strings into a timezone-aware UTC datetime."""
    date_str = date_str.strip()
    if date_str.endswith("Z"):
        date_str = date_str[:-1] + "+00:00"
    if " " in date_str and "T" not in date_str:
        date_str = date_str.replace(" ", "T")
    dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def transliterate_german(text: str) -> str:
    """Transliterates German umlauts and eszett for filesystem friendliness."""
    mapping = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
    }
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text


def sanitize_filename(name: str) -> str:
    """Removes invalid filename characters and replaces '&' with 'and'."""
    clean = html.unescape(name)
    clean = re.sub(r"[\s_]*&[\s_]*", "_and_", clean)
    clean = clean.replace("&", "and")
    clean = re.sub(r'[\\/*?:"<>|]', "", clean)
    clean = clean.strip().replace(" ", "_")
    clean = re.sub(r"_+", "_", clean)
    return clean[:80] if clean else "file"


def sanitize_title_slug(text: str) -> str:
    """
    Sanitizes thread title or slug for filenames and directory names.
    Normalizes unicode dashes, replaces '&' with 'and', removes invalid characters, collapses hyphens.
    """
    if not text:
        return "thread"
    clean = urllib.parse.unquote(str(text).strip())
    clean = html.unescape(clean)
    clean = re.sub(r"^\d+-", "", clean)
    clean = re.sub(r"[\u2010-\u2015\u2212]", "-", clean)
    clean = transliterate_german(clean)
    clean = re.sub(r"[\s-]*&[\s-]*", "-and-", clean)
    clean = clean.replace("&", "and")
    clean = re.sub(r'[\\/*?:"<>|]', "", clean)
    clean = re.sub(r"\s+", "-", clean)
    if clean and clean[0].islower():
        clean = clean[0].upper() + clean[1:]
    clean = re.sub(r"-+", "-", clean)
    clean = clean.strip("- .")
    return clean[:100] if clean else "thread"


def extract_board_info_from_url(url: str) -> Tuple[str, str]:
    """
    Extracts (board_id, slug) from a board URL.
    Example: 'https://philaforum.com/forum/board/241-l%C3%BCbeck/' -> ('241', 'Luebeck')
    """
    m = re.search(r'/board/(\d+)(?:-([^/?#]+))?', url)
    if m:
        board_id = m.group(1)
        raw_slug = m.group(2)
        if raw_slug:
            unquoted = urllib.parse.unquote(raw_slug)
            parts = [p.capitalize() if p.isalpha() else p for p in unquoted.split("-")]
            slug = sanitize_title_slug("-".join(parts))
        else:
            slug = f"Board-{board_id}"
        return (board_id, slug)
    return ("", "board")


def load_boards_registry(output_dir: str) -> dict:
    """Loads boards.json from forum directory."""
    path = os.path.join(output_dir, BOARDS_FILENAME)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            print(f"Warning: Could not read {path}: {e}")
    return {}


def save_boards_registry(output_dir: str, registry: dict) -> None:
    """Saves boards.json in forum directory."""
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


def find_board_entry(registry: dict, identifier: str) -> Optional[Tuple[str, dict]]:
    """Looks up a board in the registry by key, name, board_id, or board_url."""
    if not identifier:
        return None
    if identifier in registry and not identifier.startswith("_") and isinstance(registry[identifier], dict):
        return (identifier, registry[identifier])

    id_lower = identifier.lower().strip()
    for k, v in registry.items():
        if not k.startswith("_") and isinstance(v, dict):
            if k.lower().strip() == id_lower:
                return (k, v)
            if str(v.get("name", "")).strip().lower() == id_lower:
                return (k, v)
            if str(v.get("board_id", "")).strip() == identifier.strip():
                return (k, v)
            b_url = str(v.get("board_url", "")).rstrip("/")
            if b_url and (id_lower in b_url.lower() or b_url.lower() in id_lower):
                return (k, v)
    return None


def fetch_url(url: str, headers: Optional[dict] = None) -> str:
    """Fetches text content from a URL respecting rate limits."""
    if not url or "images/avatars/" in url.lower() or "/avatars/" in url.lower():
        return ""

    if GLOBAL_RATE_LIMITER is not None:
        GLOBAL_RATE_LIMITER.wait()

    req_headers = {"User-Agent": USER_AGENT}
    if COOKIE:
        req_headers["Cookie"] = COOKIE
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        raw = resp.read()
        return raw.decode(charset, errors="replace")


def is_decorative_image(url: str, attrs: str = "") -> bool:
    """Returns True if image is a smiley, emoji, icon, or avatar."""
    low_url = (url or "").lower()
    low_attrs = (attrs or "").lower()
    return (
        any(k in low_url for k in ["/smilies/", "/smiley/", "/emojis/", "/emoji/", "/avatars/", "/avatar/", "pagelogo", "smilies/emojione"])
        or any(k in low_attrs for k in ["smiley", "wcemoji", "useravatarimage"])
    )


def get_image_filename(url: str, mime: str = "image/jpeg") -> str:
    """Generates a stable, safe image filename."""
    ext_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/avif": ".avif",
        "image/svg+xml": ".svg",
    }
    default_ext = ext_map.get(mime.lower(), ".jpg")

    att_match = re.search(r'/attachment/(\d+)(?:-([^/?#]+))?', url)
    if att_match:
        att_id = att_match.group(1)
        raw_name = att_match.group(2)
        if raw_name:
            unquoted = urllib.parse.unquote(raw_name)
            name, ext = os.path.splitext(unquoted)
            if not ext:
                ext = default_ext
            clean_name = sanitize_filename(transliterate_german(name))
            clean_ext = sanitize_filename(ext).lower()
            return f"{att_id}-{clean_name}{clean_ext}"
        return f"{att_id}-attachment{default_ext}"

    parsed = urllib.parse.urlparse(url)
    basename = os.path.basename(parsed.path)
    if basename:
        name, ext = os.path.splitext(urllib.parse.unquote(basename))
        if not ext:
            ext = default_ext
        clean_name = sanitize_filename(transliterate_german(name))
        clean_ext = sanitize_filename(ext).lower()
        return f"{clean_name}{clean_ext}"

    h = base64.urlsafe_b64encode(url.encode()).decode("ascii")[:16]
    return f"img_{h}{default_ext}"


def fetch_and_save_image(
    url: str,
    base_url: str = "https://philaforum.com/",
    images_dir: Optional[str] = None,
    image_link_prefix: str = "../images/",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Downloads image to images_dir and returns (relative_src, relative_href).
    Uses image caching to avoid redundant downloads.
    """
    if not url:
        return (None, None)

    if url.startswith("data:"):
        return (None, None)

    if "smilies/emojione" in url.lower() or "images/avatars/" in url.lower() or "/avatars/" in url.lower():
        return (None, None)

    full_url = urllib.parse.urljoin(base_url, url)
    full_url = re.sub(r'(\/attachment\/\d+[^"\'>\s]*)\?thumbnail=1', r"\1", full_url)

    if "smilies/emojione" in full_url.lower() or "images/avatars/" in full_url.lower() or "/avatars/" in full_url.lower():
        return (None, None)

    if not images_dir:
        return (None, None)

    with _IMAGE_CACHE_LOCK:
        if full_url in _IMAGE_CACHE:
            return _IMAGE_CACHE[full_url]

    # Check if file already exists locally in images_dir (${output-dir}/images)
    if images_dir and os.path.isdir(images_dir):
        provisional_name = get_image_filename(full_url)
        cand_path = os.path.join(images_dir, provisional_name)
        matched_file = None

        if os.path.isfile(cand_path) and os.path.getsize(cand_path) > 0:
            matched_file = provisional_name
        else:
            # Fallback 1: check for existing file matching attachment ID prefix (e.g. 173480-*.jpg)
            m_att = re.search(r"/attachment/(\d+)", full_url, re.IGNORECASE)
            if m_att:
                att_prefix = f"{m_att.group(1)}-"
                try:
                    for f in os.listdir(images_dir):
                        full_f = os.path.join(images_dir, f)
                        if f.startswith(att_prefix) and os.path.isfile(full_f) and os.path.getsize(full_f) > 0:
                            matched_file = f
                            cand_path = full_f
                            break
                except Exception:
                    pass

        # Fallback 2: check for matching stem with alternate image extension
        if not matched_file:
            stem, _ = os.path.splitext(provisional_name)
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"]:
                alt_path = os.path.join(images_dir, f"{stem}{ext}")
                if os.path.isfile(alt_path) and os.path.getsize(alt_path) > 0:
                    matched_file = f"{stem}{ext}"
                    cand_path = alt_path
                    break

        if matched_file:
            prefix = image_link_prefix.rstrip("/")
            rel_path = f"{prefix}/{matched_file}"
            print(f"    [Image] Already exists, skipping: {matched_file}")
            with _IMAGE_CACHE_LOCK:
                _IMAGE_CACHE[full_url] = (rel_path, rel_path)
            return (rel_path, rel_path)

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
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            mime = resp.headers.get_content_type() or "image/jpeg"

            if images_dir:
                os.makedirs(images_dir, exist_ok=True)
                fname = get_image_filename(full_url, mime)
                local_path = os.path.join(images_dir, fname)
                with _IMAGE_CACHE_LOCK:
                    if not (os.path.isfile(local_path) and os.path.getsize(local_path) > 0):
                        with open(local_path, "wb") as f:
                            f.write(raw)
                        print(f"    [Image] Downloaded {fname}")
                prefix = image_link_prefix.rstrip("/")
                rel_path = f"{prefix}/{fname}"
                with _IMAGE_CACHE_LOCK:
                    _IMAGE_CACHE[full_url] = (rel_path, rel_path)
                return (rel_path, rel_path)
            return (full_url, full_url)
    except Exception as e:
        print(f"  Warning: Could not download image {full_url}: {e}")
        return (None, None)


def embed_and_link_images(
    html_content: str,
    base_url: str = "https://philaforum.com/",
    images_dir: Optional[str] = None,
    image_link_prefix: str = "../images/",
) -> str:
    """
    Downloads images to images_dir and rewrites image src and href attributes to
    relative links (default: ../images/<filename>).
    Upgrades thumbnail URLs (?thumbnail=1) to original full-resolution attachments.
    """
    # 1. Upgrade thumbnails to original full-resolution attachments
    html_content = re.sub(r'(\/attachment\/\d+[^"\'>\s]*)\?thumbnail=1', r"\1", html_content)

    if images_dir:
        attachment_matches = set(re.findall(r'\/attachment\/\d+', html_content))
        if attachment_matches:
            print(f"  Processing {len(attachment_matches)} unique image attachment(s)...")

    # 2. Process anchors wrapping <img> tags
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

        target_img_url = orig_src
        if orig_href and ("attachment" in orig_href or re.search(r"\.(jpe?g|png|gif|webp)", orig_href, re.IGNORECASE)):
            target_img_url = orig_href

        # Discard smilies/emojione, data URIs, and avatar images completely
        if (
            target_img_url.startswith("data:")
            or orig_src.startswith("data:")
            or "smilies/emojione" in target_img_url.lower()
            or "images/avatars/" in target_img_url.lower()
            or "/avatars/" in target_img_url.lower()
            or "smilies/emojione" in orig_src.lower()
            or "images/avatars/" in orig_src.lower()
            or "/avatars/" in orig_src.lower()
            or "smilies/emojione" in attrs.lower()
            or "images/avatars/" in attrs.lower()
            or "/avatars/" in attrs.lower()
            or "useravatar" in attrs.lower()
            or "useravatar" in inner.lower()
        ):
            return ""

        is_decorative = is_decorative_image(target_img_url, attrs)
        rel_src, rel_href = None, None
        if target_img_url and not is_decorative:
            rel_src, rel_href = fetch_and_save_image(
                target_img_url, base_url, images_dir, image_link_prefix=image_link_prefix
            )

        new_inner = inner
        if rel_src:
            new_inner = re.sub(
                r'(<img\b[^>]*\bsrc=["\'])[^"\']*(["\'])',
                rf"\g<1>{rel_src}\2",
                new_inner,
                count=1,
                flags=re.IGNORECASE,
            )
        new_inner = re.sub(r'\s*\b(width|height)=["\']\d+["\']', "", new_inner, flags=re.IGNORECASE)

        if rel_href and not is_decorative:
            clean_attrs = re.sub(r'\s*\bhref=["\'][^"\']*["\']', "", attrs, flags=re.IGNORECASE).strip()
            clean_attrs = re.sub(r'\s*\btarget=["\'][^"\']*["\']', "", clean_attrs, flags=re.IGNORECASE).strip()
            clean_attrs = re.sub(r"\bjsImageViewer\b", "", clean_attrs).strip()
            attr_str = f" {clean_attrs}" if clean_attrs else ""
            return f'<a href="{rel_href}"{attr_str} target="_blank" title="Click to view full image">{new_inner}</a>'
        else:
            clean_attrs = re.sub(r'\s*\bhref=["\'][^"\']*["\']', "", attrs, flags=re.IGNORECASE).strip()
            clean_attrs = re.sub(r"\bjsImageViewer\b", "", clean_attrs).strip()
            attr_str = f" {clean_attrs}" if clean_attrs else ""
            return f"<span{attr_str}>{new_inner}</span>"

    html_content = anchor_pattern.sub(process_anchor_match, html_content)

    # 3. Process standalone <img> tags
    img_pattern = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)

    def process_standalone_img(m):
        full_tag = m.group(0)
        attrs = m.group(1)

        src_m = re.search(r'\bsrc=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
        if not src_m:
            return full_tag
        src = src_m.group(1)

        # Discard smilies/emojione, avatar images, and avatar classes completely
        if (
            "smilies/emojione" in src.lower()
            or "images/avatars/" in src.lower()
            or "/avatars/" in src.lower()
            or "smilies/emojione" in attrs.lower()
            or "images/avatars/" in attrs.lower()
            or "/avatars/" in attrs.lower()
            or "useravatarimage" in attrs.lower()
            or "useravatar" in attrs.lower()
        ):
            return ""

        if src.startswith("data:") or src.startswith("../images/") or src.startswith("images/"):
            return full_tag

        is_decorative = is_decorative_image(src, attrs)
        rel_src, rel_href = None, None
        if not is_decorative:
            rel_src, rel_href = fetch_and_save_image(
                src, base_url, images_dir, image_link_prefix=image_link_prefix
            )
        new_tag = full_tag
        if rel_src:
            new_tag = re.sub(
                r'(\bsrc=["\'])[^"\']*(["\'])',
                rf"\g<1>{rel_src}\2",
                new_tag,
                count=1,
                flags=re.IGNORECASE,
            )
        new_tag = re.sub(r'\s*\b(width|height)=["\']\d+["\']', "", new_tag, flags=re.IGNORECASE)

        if rel_href and not is_decorative:
            return f'<a href="{rel_href}" target="_blank" title="Click to view full image">{new_tag}</a>'
        return new_tag

    html_content = img_pattern.sub(process_standalone_img, html_content)

    # 4. Process attachment file cards without <img>
    attachment_card_pattern = re.compile(
        r'<a\b([^>]*\bhref=["\']([^"\']*\/attachment\/\d+[^"\']*)["\'][^>]*)>((?:(?!</?a\b).)*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    def process_attachment_card(m):
        full_attrs = m.group(1)
        href_val = m.group(2)
        inner = m.group(3)

        if "<img" in inner.lower() or "../images/" in full_attrs or "images/" in full_attrs:
            return m.group(0)

        is_image_attachment = bool(
            re.search(r'[-.](jpe?g|png|gif|webp)(?:/|$|\b)', href_val, re.IGNORECASE)
            or re.search(r'\.(jpe?g|png|gif|webp)\b', inner, re.IGNORECASE)
            or "file-image" in inner.lower()
        )

        if not is_image_attachment:
            return m.group(0)

        rel_src, rel_href = fetch_and_save_image(href_val, base_url, images_dir, image_link_prefix=image_link_prefix)

        if rel_src and rel_href:
            clean_attrs = re.sub(r'\s*\bhref=["\'][^"\']*["\']', '', full_attrs, flags=re.IGNORECASE).strip()
            clean_attrs = re.sub(r'\s*\btarget=["\'][^"\']*["\']', '', clean_attrs, flags=re.IGNORECASE).strip()
            clean_attrs = re.sub(r'\bjsTooltip\b', '', clean_attrs).strip()
            attr_str = f" {clean_attrs}" if clean_attrs else ""
            img_tag = (
                f'<div class="attachmentImagePreview" style="margin-bottom:8px;">'
                f'<img class="embeddedImage" src="{rel_src}" style="max-width:100%;max-height:850px;object-fit:contain;display:block;margin:0 auto;">'
                f'</div>'
            )
            return f'<a href="{rel_href}"{attr_str} target="_blank" title="Click to view full image">{img_tag}{inner}</a>'
        else:
            clean_attrs = re.sub(r'\s*\bhref=["\'][^"\']*["\']', '', full_attrs, flags=re.IGNORECASE).strip()
            clean_attrs = re.sub(r'\bjsTooltip\b', '', clean_attrs).strip()
            attr_str = f" {clean_attrs}" if clean_attrs else ""
            return f'<span{attr_str} title="Attachment preview unavailable">{inner}</span>'

    html_content = attachment_card_pattern.sub(process_attachment_card, html_content)

    return html_content


def remove_tag_blocks(html_text: str, start_tag_pattern: str, tag_name: str) -> str:
    """
    Removes all blocks matching start_tag_pattern and their closing tags, handling nesting.
    Executes in a single linear O(N) scan without quadratic repeated searches or string re-allocations.
    """
    if not html_text:
        return html_text
    start_re = re.compile(start_tag_pattern, re.IGNORECASE)
    token_pattern = re.compile(rf'(<{tag_name}\b[^>]*>)|(</{tag_name}\s*>)', re.IGNORECASE)

    chunks = []
    cursor = 0
    total_len = len(html_text)

    while cursor < total_len:
        m = start_re.search(html_text, cursor)
        if not m:
            chunks.append(html_text[cursor:])
            break

        chunks.append(html_text[cursor:m.start()])
        content_start = m.end()
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

        if end_pos is not None:
            cursor = end_pos
        else:
            next_tag = html_text.find(f"</{tag_name}>", content_start)
            if next_tag != -1:
                cursor = next_tag + len(tag_name) + 3
            else:
                cursor = total_len
            break

    return "".join(chunks)


def remove_nav_from_content_header(html_text: str) -> str:
    """Removes <nav> elements located inside <header class="contentHeader"> or #content > header."""
    header_pattern = re.compile(
        r'(<header\b[^>]*class="[^"]*contentHeader[^"]*"[^>]*>)(.*?)(</header>)',
        re.DOTALL | re.IGNORECASE,
    )

    def repl(m):
        open_h = m.group(1)
        body_h = m.group(2)
        close_h = m.group(3)
        cleaned_body = remove_tag_blocks(body_h, r'<nav\b[^>]*>', 'nav')
        return f"{open_h}{cleaned_body}{close_h}"

    html_text = header_pattern.sub(repl, html_text)

    # Also handle #content > header > nav when header lacks class contentHeader
    content_header_pattern = re.compile(
        r'(<[^>]*\bid=["\']content["\'][^>]*>\s*<header\b[^>]*>)(.*?)(</header>)',
        re.DOTALL | re.IGNORECASE,
    )

    def repl_content_header(m):
        open_h = m.group(1)
        body_h = m.group(2)
        close_h = m.group(3)
        cleaned_body = remove_tag_blocks(body_h, r'<nav\b[^>]*>', 'nav')
        return f"{open_h}{cleaned_body}{close_h}"

    html_text = content_header_pattern.sub(repl_content_header, html_text)
    return html_text


def remove_wcf13_footer(html_text: str) -> str:
    """
    Removes elements matching #wcf13 > div > footer or any footer inside #wcf13.
    Also removes #wcf13 if it only contains the footer/empty containers.
    """
    wcf13_pattern = re.compile(r'<([a-zA-Z0-9]+)\b[^>]*\bid=["\']wcf13["\'][^>]*>', re.IGNORECASE)

    while True:
        m = wcf13_pattern.search(html_text)
        if not m:
            break
        tag_name = m.group(1).lower()
        start_pos = m.start()
        content_start = m.end()

        token_pattern = re.compile(rf'(<{tag_name}\b[^>]*>)|(</{tag_name}\s*>)', re.IGNORECASE)
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
            break

        full_block = html_text[start_pos:end_pos]
        close_tag_len = len(f"</{tag_name}>")
        inner_content = html_text[content_start:end_pos - close_tag_len]

        cleaned_inner = remove_tag_blocks(inner_content, r'<footer\b[^>]*>', 'footer')

        stripped_inner = re.sub(r'<[^>]+>', '', cleaned_inner).strip()
        if not stripped_inner:
            html_text = html_text[:start_pos] + html_text[end_pos:]
        else:
            new_block = html_text[start_pos:content_start] + cleaned_inner + html_text[end_pos - close_tag_len:end_pos]
            html_text = html_text[:start_pos] + new_block + html_text[end_pos:]
            if new_block == full_block:
                break

        wcf13_match = re.search(r'<([a-zA-Z0-9]+)\b[^>]*\bid=["\']wcf13["\'][^>]*>', html_text, re.IGNORECASE)
        if not wcf13_match or wcf13_match.start() == start_pos:
            break

    html_text = remove_tag_blocks(html_text, r'<footer\b[^>]*\bid=["\']wcf13["\'][^>]*>', 'footer')
    return html_text


def prune_unwanted_html_elements(html_content: str) -> str:
    """
    Prunes unwanted WoltLab forum chrome elements and scripts from the HTML output:
    1. <li class="lastModifiedLogEntry"> (edit log notes)
    2. <li class="messageQuickReply"> (quick reply form)
    3. <div class="boxesFooterBoxes"> / #boxesFooterBoxes (footer boxes)
    4. <div class="pageFooterStickyNotice"> (#tpl_wbb_thread > div.pageFooterStickyNotice)
    5. Elements with id="follow" (#follow)
    6. <nav> inside <header class="contentHeader"> (#content > header > nav)
    7. <img> and wrapping <a> with src containing "smilies/emojione"
    8. #wcf13 > div > footer (#wcf13 dialog footers)
    9. <div class="messageFooterGroup"> (article > div > footer > div.messageFooterGroup)
    10. User avatars (.userAvatar, .contentHeaderIcon, images/avatars/)
    11. External and inline WoltLab/tracking <script> tags
    """
    if not html_content:
        return html_content

    # 1. Deduplicate modificationLogEntry: retain only a single messageList > li.modificationLogEntry (specifically lastModificationLogEntry)
    html_content, _ = clean_modification_log_entries(html_content)

    # Fix blockquote display to ensure block layout instead of CSS grid
    html_content, _ = fix_blockquote_display(html_content)

    # Strip unwanted <script> tags (WoltLab scripts, trackers, inline configs)
    html_content, _ = strip_unwanted_scripts(html_content)

    # Remove any legacy / mock lastModifiedLogEntry elements
    html_content = remove_tag_blocks(
        html_content,
        r'<li\b[^>]*class=["\'][^"\']*lastMod[io]fiedLogEntry[^"\']*["\'][^>]*>',
        'li',
    )

    # 2. Remove #messageQuickReply (id="messageQuickReply") and elements with class messageQuickReply
    quick_reply_match = re.search(r'<([a-zA-Z0-9]+)\b[^>]*\bid=["\']messageQuickReply["\'][^>]*>', html_content, re.IGNORECASE)
    while quick_reply_match:
        tag_name = quick_reply_match.group(1).lower()
        html_content = remove_tag_blocks(html_content, rf'<{tag_name}\b[^>]*\bid=["\']messageQuickReply["\'][^>]*>', tag_name)
        quick_reply_match = re.search(r'<([a-zA-Z0-9]+)\b[^>]*\bid=["\']messageQuickReply["\'][^>]*>', html_content, re.IGNORECASE)

    html_content = remove_tag_blocks(
        html_content,
        r'<li\b[^>]*(?:id=["\']messageQuickReply["\']|class=["\'][^"\']*messageQuickReply[^"\']*)[^>]*>',
        'li',
    )
    html_content = remove_tag_blocks(
        html_content,
        r'<div\b[^>]*class=["\'][^"\']*messageQuickReply[^"\']*["\'][^>]*>',
        'div',
    )

    # 3. Remove <div> with class or id boxesFooterBoxes
    html_content = remove_tag_blocks(html_content, r'<div\b[^>]*(?:class="[^"]*boxesFooterBoxes[^"]*"|id="boxesFooterBoxes")[^>]*>', 'div')

    # 4. Remove #tpl_wbb_thread > div.pageFooterStickyNotice
    html_content = remove_tag_blocks(html_content, r'<div\b[^>]*class="[^"]*pageFooterStickyNotice[^"]*"[^>]*>', 'div')

    # 5. Remove elements with id="follow"
    follow_match = re.search(r'<([a-zA-Z0-9]+)\b[^>]*\bid=["\']follow["\'][^>]*>', html_content, re.IGNORECASE)
    while follow_match:
        tag_name = follow_match.group(1).lower()
        html_content = remove_tag_blocks(html_content, rf'<{tag_name}\b[^>]*\bid=["\']follow["\'][^>]*>', tag_name)
        follow_match = re.search(r'<([a-zA-Z0-9]+)\b[^>]*\bid=["\']follow["\'][^>]*>', html_content, re.IGNORECASE)

    # 6. Remove #content > header > nav
    html_content = remove_nav_from_content_header(html_content)

    # 7. Remove any <a> wrapping smilies/emojione and standalone smilies/emojione <img>
    html_content = re.sub(
        r'<a\b[^>]*>((?:(?!</?a\b).)*?<img\b[^>]*\bsrc=["\'][^"\']*smilies\/emojione[^"\']*["\'][^>]*>(?:(?!</?a\b).)*?)</a>',
        '',
        html_content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html_content = re.sub(
        r'<img\b[^>]*\bsrc=["\'][^"\']*smilies\/emojione[^"\']*["\'][^>]*>',
        '',
        html_content,
        flags=re.IGNORECASE,
    )

    # 8. Remove #wcf13 > div > footer
    html_content = remove_wcf13_footer(html_content)

    # 9. Remove <div class="messageFooterGroup"> (article > div > footer > div.messageFooterGroup)
    html_content = remove_tag_blocks(html_content, r'<div\b[^>]*class="[^"]*messageFooterGroup[^"]*"[^>]*>', 'div')

    # 10. Remove user avatars and avatar containers (.userAvatar, .contentHeaderIcon, images/avatars/)
    html_content = remove_tag_blocks(html_content, r'<div\b[^>]*class="[^"]*userAvatar[^"]*"[^>]*>', 'div')
    html_content = remove_tag_blocks(html_content, r'<div\b[^>]*class="[^"]*contentHeaderIcon[^"]*"[^>]*>', 'div')

    html_content = re.sub(
        r'<(a|span)\b[^>]*>\s*<img\b[^>]*(?:src=["\'][^"\']*(?:images\/avatars\/|\/avatars\/)[^"\']*["\']|class=["\'][^"\']*userAvatarImage[^"\']*["\'])[^>]*>\s*</\1>',
        '',
        html_content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html_content = re.sub(
        r'<a\b[^>]*>((?:(?!</?a\b).)*?<img\b[^>]*\bsrc=["\'][^"\']*(?:images\/avatars\/|\/avatars\/)[^"\']*["\'][^>]*>(?:(?!</?a\b).)*?)</a>',
        '',
        html_content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html_content = re.sub(
        r'<a\b[^>]*\bhref=["\'][^"\']*(?:images\/avatars\/|\/avatars\/)[^"\']*["\'][^>]*>(?:(?!</?a\b).)*?</a>',
        '',
        html_content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html_content = re.sub(
        r'<img\b[^>]*\bsrc=["\'][^"\']*(?:images\/avatars\/|\/avatars\/)[^"\']*["\'][^>]*>',
        '',
        html_content,
        flags=re.IGNORECASE,
    )
    html_content = re.sub(
        r'<img\b[^>]*\bclass=["\'][^"\']*userAvatarImage[^"\']*["\'][^>]*>',
        '',
        html_content,
        flags=re.IGNORECASE,
    )

    return html_content


def sanitize_thread_html(
    html_content: str,
    base_url: str = "https://philaforum.com/",
    images_dir: Optional[str] = None,
    image_link_prefix: str = "../images/",
) -> str:
    """
    Sanitizes WoltLab forum thread HTML into clean, printer-friendly reader format:
    - Prunes unwanted chrome elements (edit notes, quick reply, footer boxes, sticky notices, follow button, header nav, smilies/emojione).
    - Strips <base href> tags.
    - Saves images locally into images_dir and links them with image_link_prefix.
    - Injects clean responsive and printer-friendly CSS stylesheet.
    - Hides forum chrome (navigation, footers, search, reactions, sidebars, ads).
    """
    # 0. Prune unwanted HTML chrome elements and smilies/emojione
    html_content = prune_unwanted_html_elements(html_content)

    # 1. Strip <base href> tags so relative filesystem paths resolve correctly
    html_content = re.sub(r"<base\b[^>]*>", "", html_content, flags=re.IGNORECASE)

    # 2. Download images and rewrite relative image links
    html_content = embed_and_link_images(html_content, base_url, images_dir, image_link_prefix=image_link_prefix)

    # 3. Inject printer-friendly stylesheet
    print_styles = """
    <style id="scraper-print-stylesheet">
    @media screen, print {
        :root {
            --wcfLayoutMinWidth: 0px !important;
            --wcfLayoutMaxWidth: 100% !important;
        }
        html, body {
            width: 100% !important;
            max-width: 1600px !important;
            margin: 0 auto !important;
            padding: 12px 20px !important;
            box-sizing: border-box !important;
            background: #ffffff !important;
            color: #1a1a1a !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
            font-size: 11pt !important;
            line-height: 1.55 !important;
        }
        @media screen and (max-width: 1600px) {
            html, body {
                width: 100% !important;
                max-width: 100% !important;
            }
        }
        .layoutBoundary, #main, .main {
            min-width: 0 !important;
            max-width: 100% !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        .content, .content.content--sidebar-right, .sidebar + .content {
            flex: 1 1 100% !important;
            max-width: 100% !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        .message {
            display: flex !important;
            flex-direction: row !important;
            width: 100% !important;
            box-sizing: border-box !important;
            margin-bottom: 24px !important;
            padding-bottom: 16px !important;
            border-bottom: 1px solid #e0e0e0 !important;
        }
        .userAvatar, .contentHeaderIcon, .userAvatarImage {
            display: none !important;
        }
        .messageSidebar {
            flex: 0 0 120px !important;
            width: 120px !important;
            max-width: 120px !important;
            font-size: 9pt !important;
            color: #555555 !important;
            border-right: 1px solid #f0f0f0 !important;
            padding-right: 12px !important;
            margin-right: 16px !important;
        }
        .messageContent {
            flex: 1 1 auto !important;
            min-width: 0 !important;
            word-break: break-word !important;
            overflow-wrap: break-word !important;
        }
        .messageHeader {
            margin-bottom: 8px !important;
            font-size: 9.5pt !important;
            color: #666666 !important;
        }
        .messageBody, .messageText {
            font-size: 11pt !important;
            line-height: 1.55 !important;
        }
        blockquote, .quoteBox {
            display: block !important;
            grid-template-columns: none !important;
            margin: 12px 0 !important;
            padding: 10px 16px !important;
            border-left: 4px solid #0066cc !important;
            background-color: #f7f9fb !important;
            color: #333333 !important;
            font-style: italic !important;
        }
        .contentHeader {
            margin-bottom: 24px !important;
            padding-bottom: 12px !important;
            border-bottom: 2px solid #0066cc !important;
        }
        .contentTitle {
            font-size: 20pt !important;
            font-weight: 700 !important;
            color: #111111 !important;
            margin: 0 0 6px 0 !important;
        }
        .messageAttachmentList {
            display: block !important;
            margin-top: 16px !important;
        }
        .messageAttachment {
            display: block !important;
            max-width: 100% !important;
            margin-bottom: 12px !important;
        }
        .attachmentImagePreview {
            display: block !important;
            text-align: center !important;
            margin: 10px 0 !important;
        }
        img, .embeddedImage, .attachmentImagePreview img {
            max-width: 100% !important;
            max-height: 850px !important;
            height: auto !important;
            object-fit: contain !important;
            border-radius: 4px !important;
        }
        /* Hide forum navigation, headers, footers, sidebars, reactions, avatars, ads */
        #pageHeaderContainer, #pageHeader, #pageFooter,
        #wcf13 > div > footer, #wcf13, .messageFooterGroup,
        .pageNavigation, .boxesTop, .boxesBottom, .boxesSidebarLeft, .boxesSidebarRight,
        .messageGroupOptions, .wcfPostSignature, .wcfAdLocation,
        woltlab-core-pagination, .contentInteraction,
        .wcfCookieConsent, #topMenu, .mainMenu, .messageShareButtons,
        .breadcrumbs, .reactionType, .wcfReactions {
            display: none !important;
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
            }
        }
        .contentHeader, .messageHeader {
            page-break-after: avoid !important;
            break-after: avoid !important;
        }
        img, figure, blockquote {
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

    cleanup_script = """
    <script id="scraper-cleanup-wcf">
    (function() {
        function cleanupWcfFooter() {
            var el = document.querySelector("#wcf13 > div > footer");
            if (el) el.remove();
            document.querySelectorAll(".messageFooterGroup, article > div > footer > div.messageFooterGroup").forEach(function(g) {
                g.remove();
            });
            document.querySelectorAll(".userAvatar, .contentHeaderIcon, .userAvatarImage, img[src*='images/avatars/']").forEach(function(a) {
                a.remove();
            });
        }
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", cleanupWcfFooter);
        } else {
            cleanupWcfFooter();
        }
        try {
            var obs = new MutationObserver(cleanupWcfFooter);
            obs.observe(document.documentElement, { childList: true, subtree: true });
        } catch (e) {}
    })();
    </script>
    """
    if "</body>" in html_content:
        html_content = html_content.replace("</body>", f"{cleanup_script}\n</body>", 1)
    elif "</BODY>" in html_content:
        html_content = html_content.replace("</BODY>", f"{cleanup_script}\n</BODY>", 1)
    else:
        html_content = html_content + cleanup_script

    return html_content


def extract_pagination_count(html_content: str) -> int:
    """Extracts total pages of a thread from pagination elements."""
    m = re.search(r'data-pages="(\d+)"', html_content)
    if m:
        return int(m.group(1))

    m_wcf = re.search(r'<woltlab-core-pagination\b[^>]*\bcount="(\d+)"', html_content, re.IGNORECASE)
    if m_wcf:
        return int(m_wcf.group(1))

    page_numbers = [int(p) for p in re.findall(r'[?&]pageNo=(\d+)', html_content)]
    if page_numbers:
        return max(page_numbers)

    return 1


def find_tag_bounds(html_text: str, tag_name: str, class_pattern: str) -> Optional[Tuple[int, int, int, int]]:
    """Finds (start_pos, content_start, closing_start, closing_end) handling nesting."""
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
    """Extracts the inner HTML of the thread's messageList container."""
    bounds = find_tag_bounds(html_content, "ul", "messageList")
    if bounds:
        return html_content[bounds[1]:bounds[2]].strip()

    articles = re.findall(
        r'<article\b[^>]*class="[^"]*message[^"]*"[^>]*>.*?</article>',
        html_content,
        re.DOTALL | re.IGNORECASE,
    )
    if articles:
        return "\n".join(articles)
    return ""


def combine_thread_pages(base_html: str, additional_pages_html: List[str]) -> str:
    """Combines posts from multiple thread pages into a single seamless document."""
    if not additional_pages_html:
        return base_html

    collected_posts = [p for page in additional_pages_html if (p := extract_thread_posts(page))]
    if not collected_posts:
        return base_html

    combined_posts_str = "\n".join(collected_posts)
    base_bounds = find_tag_bounds(base_html, "ul", "messageList")
    if base_bounds:
        res = (
            base_html[: base_bounds[2]]
            + "\n<!-- Additional Forum Page Posts Appended -->\n"
            + combined_posts_str
            + "\n"
            + base_html[base_bounds[2] :]
        )
    else:
        found_closing = False
        res = ""
        for closing_tag in ["</main>", "</section>", "</body>"]:
            pos = base_html.lower().rfind(closing_tag)
            if pos != -1:
                res = (
                    base_html[:pos]
                    + "\n<!-- Additional Forum Page Posts Appended -->\n"
                    + combined_posts_str
                    + "\n"
                    + base_html[pos:]
                )
                found_closing = True
                break
        if not found_closing:
            res = base_html + "\n" + combined_posts_str

    res, _ = clean_modification_log_entries(res)
    return res


def extract_threads_from_board(html_content: str, base_url: str = "https://philaforum.com/") -> List[ThreadInfo]:
    """Extracts thread links and metadata from a board page."""
    threads: List[ThreadInfo] = []

    pattern = re.compile(
        r'<li\b[^>]*class="[^"]*tabularListRow[^"]*"[^>]*>(.*?)</li>',
        re.DOTALL | re.IGNORECASE,
    )

    for match in pattern.finditer(html_content):
        row = match.group(1)

        link_m = re.search(
            r'<h[23]\b[^>]*class="[^"]*wbbTopicLink[^"]*"[^>]*>\s*<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            row,
            re.DOTALL | re.IGNORECASE,
        )
        if not link_m:
            link_m = re.search(
                r'<a\b[^>]*class="[^"]*wbbTopicLink[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                row,
                re.DOTALL | re.IGNORECASE,
            )
        if not link_m:
            continue

        raw_url = link_m.group(1).strip()
        raw_title = link_m.group(2).strip()
        clean_title = html.unescape(re.sub(r'<[^>]+>', '', raw_title).strip())
        full_url = urllib.parse.urljoin(base_url, raw_url)

        # Date & timestamp
        time_m = re.search(r'<time\b[^>]*datetime="([^"]+)"', row, re.IGNORECASE)
        date_str = time_m.group(1) if time_m else None
        dt = None
        ts = 0.0
        if date_str:
            try:
                dt = parse_iso_datetime(date_str)
                ts = dt.timestamp()
            except Exception:
                pass

        is_sticky = bool(re.search(r'\b(?:wbbSticky|icon-thumb-tack|sticky)\b', row, re.IGNORECASE))
        threads.append(ThreadInfo(url=full_url, title=clean_title, date_str=date_str, dt=dt, timestamp=ts, is_sticky=is_sticky))

    if not threads:
        # Fallback: scan for any /thread/\d+ links
        raw_links = re.findall(r'<a\b[^>]*href="([^"]*\/thread\/\d+[^"]*)"[^>]*>(.*?)</a>', html_content, re.DOTALL | re.IGNORECASE)
        seen_urls = set()
        for r_url, r_txt in raw_links:
            full_u = urllib.parse.urljoin(base_url, r_url).split("?")[0].rstrip("/") + "/"
            clean_t = html.unescape(re.sub(r'<[^>]+>', '', r_txt).strip())
            if full_u not in seen_urls and clean_t and not clean_t.startswith("<"):
                seen_urls.add(full_u)
                threads.append(ThreadInfo(url=full_u, title=clean_t))

    return threads


def scrape_thread(
    thread_url: str,
    forum_dir: str,
    delay: float = 1.0,
    first_page_only: bool = False,
    max_pages: Optional[int] = None,
    thread_title: Optional[str] = None,
) -> Optional[str]:
    """
    Scrapes a thread, combining all pages into a single clean HTML article.
    Downloads images to <forum_dir>/images/ and saves the sanitized German HTML
    to <forum_dir>/html/<title_slug>.html.
    Returns the path of the saved HTML file.
    """
    clean_base_url = thread_url.split("?")[0].rstrip("/") + "/"
    print(f"\n--- Scraping Thread: {thread_title or clean_base_url} ---")

    page1_url = f"{clean_base_url}?pageNo=1"
    try:
        html_p1 = fetch_url(page1_url)
    except Exception as e:
        print(f"Error fetching {page1_url}: {e}")
        return None

    total_pages = extract_pagination_count(html_p1)
    if first_page_only:
        pages_to_scrape = [1]
    elif max_pages and max_pages > 0:
        pages_to_scrape = list(range(1, min(total_pages, max_pages) + 1))
    else:
        pages_to_scrape = list(range(1, total_pages + 1))

    if not thread_title:
        title_m = re.search(r'<h1[^>]*class="[^"]*contentTitle[^"]*"[^>]*>(.*?)</h1>', html_p1, re.DOTALL | re.IGNORECASE)
        if title_m:
            thread_title = html.unescape(re.sub(r'<[^>]+>', '', title_m.group(1)).strip())
        if not thread_title:
            slug_m = re.search(r'/thread/([^/?]+)', clean_base_url)
            thread_title = slug_m.group(1) if slug_m else "thread"

    title_slug = sanitize_title_slug(thread_title)

    images_dir = os.path.join(forum_dir, "images")
    html_dir = os.path.join(forum_dir, "html")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(html_dir, exist_ok=True)

    additional_pages: List[str] = []
    for p in pages_to_scrape[1:]:
        p_url = f"{clean_base_url}?pageNo={p}"
        print(f"  Fetching page {p}/{total_pages}: {p_url}")
        try:
            p_html = fetch_url(p_url)
            additional_pages.append(p_html)
        except Exception as e:
            print(f"  Warning: Failed to fetch page {p}: {e}")
        if delay > 0:
            time.sleep(delay)

    print(f"  Combining posts from {len(pages_to_scrape)} page(s)...")
    if additional_pages:
        combined_html = combine_thread_pages(html_p1, additional_pages)
    else:
        combined_html = html_p1

    print(f"  Sanitizing combined thread HTML ({len(combined_html) // 1024} KB) and processing images...")
    sanitized_html = sanitize_thread_html(
        combined_html,
        base_url=clean_base_url,
        images_dir=images_dir,
        image_link_prefix="../images/",
    )

    out_file = os.path.join(html_dir, f"{title_slug}.html")
    try:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(sanitized_html)
        file_size_kb = os.path.getsize(out_file) // 1024
        print(f"  [SUCCESS] Saved {out_file} ({file_size_kb} KB)")
        return out_file
    except Exception as e:
        print(f"  Error saving HTML file {out_file}: {e}")
        return None


def scrape_board(
    board_url: str,
    output_dir: Optional[str] = None,
    delay: float = 1.0,
    limit: Optional[int] = None,
    first_page_only: bool = False,
    max_pages: Optional[int] = None,
    force: bool = False,
    cookie: Optional[str] = None,
    cookie_file: Optional[str] = None,
    page: Optional[int] = None,
    from_last_page: bool = True,
) -> List[str]:
    """
    Crawls a board URL, saving German HTML threads to <output_dir>/html/<title_slug>.html,
    images to <output_dir>/images/, and tracking history in <output_dir>/boards.json.
    Supports board-level pagination:
    - If `page` is specified, crawls only that specific board page.
    - If `from_last_page` is True, starts at the last board page and crawls backward to page 1.
    - Otherwise crawls all board pages in forward order (1 to N).
    """
    global GLOBAL_RATE_LIMITER, COOKIE
    GLOBAL_RATE_LIMITER = NetworkRateLimiter(min_interval=delay)
    if cookie_file:
        COOKIE = parse_cookie_input(cookie_file)
        if COOKIE:
            print(f"Loaded credentials from cookie file: {cookie_file}")
    elif cookie:
        COOKIE = parse_cookie_input(cookie)
        if COOKIE:
            print("Loaded session cookie credentials.")

    board_id, board_slug = extract_board_info_from_url(board_url)
    forum_dir = os.path.abspath(output_dir if output_dir else os.path.join("output", board_slug))
    os.makedirs(forum_dir, exist_ok=True)

    print(f"========================================================")
    print(f"Scraping Philaforum Board: {board_url}")
    print(f"Target Forum Directory: {forum_dir}")
    print(f"Delay: {delay}s | Force: {force}")
    if page:
        print(f"Board Page Filter: Single page {page}")
    if from_last_page:
        print("Crawl Direction: Reverse (starting at last page)")
    if COOKIE:
        print("Credentials: Active session cookie configured")
    print(f"========================================================")

    registry = load_boards_registry(forum_dir)
    board_key = board_slug or f"Board-{board_id}"
    board_entry = registry.get(board_key, {})
    last_fetched_ts = board_entry.get("timestamp", 0.0)

    clean_board_url = board_url.split("?")[0].rstrip("/") + "/"

    cached_board_pages = {}
    if page is not None and page > 0:
        board_pages_to_crawl = [page]
        total_board_pages = page
        print(f"Targeting single board page: {page}")
    else:
        page1_url = f"{clean_board_url}?pageNo=1" if "?" not in board_url else board_url
        try:
            page1_html = fetch_url(page1_url)
        except Exception as e:
            print(f"Error fetching board {page1_url}: {e}")
            return []

        total_board_pages = extract_pagination_count(page1_html)
        cached_board_pages[1] = page1_html
        print(f"Discovered {total_board_pages} page(s) on board.")

        if from_last_page:
            board_pages_to_crawl = list(range(total_board_pages, 0, -1))
            print(f"--- Crawling board in reverse: Starting at last page {total_board_pages} and moving backward to 1 ---")
        else:
            board_pages_to_crawl = list(range(1, total_board_pages + 1))

    # Discover threads across board pages to crawl
    all_threads: List[ThreadInfo] = []
    for b_page in board_pages_to_crawl:
        if limit and len(all_threads) >= limit:
            break

        if b_page in cached_board_pages:
            curr_board_html = cached_board_pages.pop(b_page)
        else:
            b_url = f"{clean_board_url}?pageNo={b_page}"
            print(f"\nCrawling board page {b_page}/{total_board_pages}: {b_url}")
            try:
                curr_board_html = fetch_url(b_url)
            except Exception as e:
                print(f"Warning: Failed to fetch board page {b_page}: {e}")
                continue
            if delay > 0:
                time.sleep(delay)

        page_threads = extract_threads_from_board(curr_board_html, base_url=board_url)
        print(f"  Found {len(page_threads)} thread(s) on board page {b_page}.")

        if from_last_page:
            # WoltLab lists threads newest to oldest. In from_last_page mode,
            # reverse page threads to process oldest first
            page_threads.reverse()

        all_threads.extend(page_threads)
        if limit and len(all_threads) >= limit:
            all_threads = all_threads[:limit]
            break

    # Deduplicate while preserving order
    seen_urls = set()
    threads_to_process: List[ThreadInfo] = []
    for t in all_threads:
        if t.url not in seen_urls:
            seen_urls.add(t.url)
            threads_to_process.append(t)

    total_threads = len(threads_to_process)
    print(f"\nDiscovered {total_threads} thread(s) on board to process.")

    scraped_files: List[str] = []

    for idx, t in enumerate(threads_to_process, start=1):
        slug = sanitize_title_slug(t.title)
        expected_html = os.path.join(forum_dir, "html", f"{slug}.html")

        # Resume check: if already processed, mark as done in console and continue
        if not force and os.path.isfile(expected_html) and os.path.getsize(expected_html) > 0:
            print(f"[{idx}/{total_threads}] (Done) '{t.title}' already processed.")
            continue

        print(f"[{idx}/{total_threads}] Processing thread: '{t.title}'")
        html_path = scrape_thread(
            thread_url=t.url,
            forum_dir=forum_dir,
            delay=delay,
            first_page_only=first_page_only,
            max_pages=max_pages,
            thread_title=t.title,
        )

        if html_path:
            scraped_files.append(html_path)
            now_iso = datetime.now(timezone.utc).isoformat()
            now_ts = datetime.now(timezone.utc).timestamp()
            html_basename = os.path.basename(html_path)

            board_entry.update({
                "name": board_slug,
                "board_id": board_id,
                "board_url": board_url,
                "last_updated": t.date_str or now_iso,
                "timestamp": t.timestamp or now_ts,
                "last_thread_url": t.url,
                "last_thread_title": t.title,
                "last_html": html_basename,
            })
            board_entry["threads"] = {
                t.url: {
                    "title": t.title,
                    "html_file": html_basename,
                    "url": t.url,
                    "timestamp": t.timestamp or now_ts,
                    "last_scraped": now_iso,
                    "status": "done",
                }
            }
            registry[board_key] = board_entry
            save_boards_registry(forum_dir, registry)

        if delay > 0 and idx < total_threads:
            time.sleep(delay)

    print(f"\nScraping complete! Successfully saved {len(scraped_files)} thread(s) into {os.path.join(forum_dir, 'html')}.")
    return scraped_files


def main():
    parser = argparse.ArgumentParser(
        description="Philaforum Pure HTML Scraper (direct HTML articles with relative images)"
    )
    parser.add_argument(
        "--build-url",
        "--board-url",
        "--url",
        "-u",
        dest="board_url",
        required=True,
        help="Board URL or thread URL to scrape (required)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        help="Output directory (defaults to output/<board-slug>)",
    )
    parser.add_argument(
        "--delay",
        "-d",
        type=float,
        default=DEFAULT_DELAY,
        help=f"Politeness delay between network requests in seconds (default: {DEFAULT_DELAY})",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        help="Limit number of threads to scrape",
    )
    parser.add_argument(
        "--first-page-only",
        action="store_true",
        help="Scrape only page 1 of each thread",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Maximum pages to scrape per thread",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force re-scrape of existing articles",
    )
    parser.add_argument(
        "--cookie-file",
        help="Path to file containing session cookies/credentials (supports Netscape, JSON, key=val, or raw Cookie header)",
    )
    parser.add_argument(
        "--cookie",
        help="Optional session cookie string or path to cookie file",
    )
    parser.add_argument(
        "--page",
        "-p",
        type=int,
        default=None,
        help="Specific board page to scrape (e.g. 1, 2). If omitted, all pages are scraped.",
    )
    parser.add_argument(
        "--from-last-page",
        dest="from_last_page",
        action="store_true",
        default=True,
        help="Start scraping at the last board page and crawl backward to page 1 (default: True).",
    )
    parser.add_argument(
        "--from-first-page",
        dest="from_last_page",
        action="store_false",
        help="Start scraping at the first board page and crawl forward.",
    )

    args = parser.parse_args()
    scrape_board(
        board_url=args.board_url,
        output_dir=args.output_dir,
        delay=args.delay,
        limit=args.limit,
        first_page_only=args.first_page_only,
        max_pages=args.max_pages,
        force=args.force,
        cookie=args.cookie,
        cookie_file=args.cookie_file,
        page=args.page,
        from_last_page=args.from_last_page,
    )


if __name__ == "__main__":
    main()
