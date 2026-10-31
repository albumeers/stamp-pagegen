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
Philaforum HTML Translator
Translates German forum articles saved in <forum-folder>/html/<slug>.html
into English HTML saved in <forum-folder>/<slug>.html using local Ollama.
Updates relative image links from '../images/' to 'images/' so they resolve
seamlessly from the forum root directory.
Records translation progress in <forum-folder>/translation.json with resume support.
"""

import argparse
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "codegemma:7b"
TRANSLATION_FILENAME = "translate.json"
LEGACY_TRANSLATION_FILENAME = "translation.json"

ISO_639_1_LANGUAGES: Dict[str, str] = {
    "de": "German",
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "nl": "Dutch",
    "pt": "Portuguese",
    "ru": "Russian",
    "pl": "Polish",
    "cs": "Czech",
    "hu": "Hungarian",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
    "el": "Greek",
    "tr": "Turkish",
    "ja": "Japanese",
    "zh": "Chinese",
}


def get_language_name(code: str) -> str:
    """Returns human-readable language name for an ISO 639-1 code."""
    return ISO_639_1_LANGUAGES.get(code.strip().lower(), f"Language ({code})")


def check_ollama_available(ollama_url: str = DEFAULT_OLLAMA_URL, timeout: float = 3.0) -> bool:
    """Checks if local Ollama daemon is reachable."""
    try:
        url = urllib.parse.urljoin(ollama_url, "/api/tags")
        req = urllib.request.Request(url, headers={"User-Agent": "philaforum-translator/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def resolve_registry_path(forum_dir: str, explicit_filename: Optional[str] = None) -> str:
    """
    Resolves registry JSON path in forum_dir.
    Checks for translate.json first, then legacy translation.json.
    Defaults to translate.json if neither exists yet.
    """
    if explicit_filename:
        return os.path.join(forum_dir, explicit_filename)
    for fname in [TRANSLATION_FILENAME, LEGACY_TRANSLATION_FILENAME]:
        cand = os.path.join(forum_dir, fname)
        if os.path.isfile(cand):
            return cand
    return os.path.join(forum_dir, TRANSLATION_FILENAME)


def load_translation_registry(registry_path: str) -> dict:
    """Loads translation history from translate.json or translation.json."""
    target_path = registry_path
    if not os.path.isfile(target_path):
        dirname = os.path.dirname(os.path.abspath(registry_path))
        basename = os.path.basename(registry_path)
        alt_name = LEGACY_TRANSLATION_FILENAME if basename == TRANSLATION_FILENAME else TRANSLATION_FILENAME
        alt_path = os.path.join(dirname, alt_name)
        if os.path.isfile(alt_path):
            target_path = alt_path

    if os.path.isfile(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("translations", {})
                    return data
        except Exception as e:
            print(f"Warning: Could not read {target_path}: {e}")
    return {"translations": {}}


def save_translation_registry(registry_path: str, data: dict) -> None:
    """Saves translation history to registry JSON."""
    os.makedirs(os.path.dirname(os.path.abspath(registry_path)), exist_ok=True)
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # If the alternate registry filename also exists in the folder, keep it synchronized
    dirname = os.path.dirname(os.path.abspath(registry_path))
    basename = os.path.basename(registry_path)
    alt_name = LEGACY_TRANSLATION_FILENAME if basename == TRANSLATION_FILENAME else TRANSLATION_FILENAME
    alt_path = os.path.join(dirname, alt_name)
    if os.path.isfile(alt_path):
        try:
            with open(alt_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass


def record_translation_in_registry(
    registry_path: str,
    source_filename: str,
    translated_filename: str,
    translated_title: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    source_lang: str = "de",
    target_lang: str = "en",
    status: str = "completed",
) -> None:
    """
    Records a completed translation in registry JSON and updates last_translated_file.
    Maintains only one translation (the last one) under reg['translations'].
    """
    reg = load_translation_registry(registry_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    reg["last_translated_file"] = os.path.basename(source_filename)
    reg["last_updated"] = now_iso
    reg["model"] = model
    reg["source_lang"] = source_lang
    reg["target_lang"] = target_lang

    reg["translations"] = {
        os.path.basename(source_filename): {
            "status": status,
            "source_file": source_filename,
            "translated_file": translated_filename,
            "translated_title": translated_title or "",
            "timestamp": now_iso,
            "model": model,
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
    }
    save_translation_registry(registry_path, reg)


def clean_translated_text(translated: str, original: str) -> str:
    """Cleans up LLM conversational chatter, system prompt echoes, and markdown code blocks."""
    if not translated:
        return original
    text = translated.strip()

    # Strip surrounding quotes if wrapped
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()

    # Strip conversational chatter
    if re.search(r"^(?:Dear\s+[A-Za-z0-9_ -]+,?\s+)?(?:Thank you for your message\b|I\s+am\s+ready\s+to\s+translate\b|Please\s+(?:share|provide)\s+the\s+text\b)", text, re.IGNORECASE):
        return original

    # Strip leaked system prompt lines
    leak_patterns = [
        r"^.*?(?:You are a professional translator|You are an expert philatelic translator).*?(?:\n|$)",
        r"^.*?(?:Return ONLY the direct translation|Key philatelic terminology guidelines:).*?(?:\n|$)",
    ]
    for pat in leak_patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE | re.DOTALL).strip()

    # Strip preamble markers (e.g. "**Direct Translation:**", "Translation:")
    preamble_patterns = [
        r"^(?:\*{1,3}|#{1,6})?\s*(?:Direct\s+)?(?:English\s+)?Translation(?:\s*(?:from|into|of)[^\n:]*)?[:\*\s-]+\s*",
        r"^(?:(?:Here|As\s+requested,?\s+here)\s+is\s+the\s+(?:direct\s+)?translation\s*:\s*)",
    ]
    for pat in preamble_patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE).strip()

    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()

    return text if text else original


def query_ollama_translation(
    text: str,
    source_lang: str = "de",
    target_lang: str = "en",
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 60,
    max_retries: int = 2,
) -> str:
    """
    Translates text from source_lang to target_lang using Ollama /api/chat.
    Specialized for philatelic, postal history, and auction terminology.
    """
    clean_text = text.strip()
    if not clean_text:
        return text

    source_lang_name = get_language_name(source_lang)
    target_lang_name = get_language_name(target_lang)

    system_prompt = (
        f"You are a professional translator specializing in philatelic (stamp collecting), "
        f"postal history, and auction terminology.\n"
        f"Translate the provided text directly and accurately from {source_lang_name} into fluent, natural {target_lang_name}.\n"
        f"Output ONLY the direct translation without explanation, preamble, or conversational remarks."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Text to translate:\n{clean_text}"},
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    api_endpoint = urllib.parse.urljoin(ollama_url, "/api/chat")

    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(
                api_endpoint,
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": "philaforum-translator/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                translated = res_json.get("message", {}).get("content", "").strip()
                cleaned = clean_translated_text(translated, clean_text)
                return cleaned if cleaned else text
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1.0)
            else:
                print(f"Warning: Ollama translation failed ({e}). Keeping original text.")
                return text

    return text


def update_image_links_to_root(html_content: str, images_dirname: str = "images") -> str:
    """
    Converts relative image links from '../images/' (used inside <forum-dir>/html/)
    to 'images/' (used at <forum-dir>/). Also converts '../image/' to 'images/'.
    Strips any <base href="..."> tags.
    """
    # 1. Strip <base href> tags
    updated = re.sub(r"<base\b[^>]*>", "", html_content, flags=re.IGNORECASE)

    # 2. Convert ../images/ or ../image/ to images/ (or images_dirname/)
    target_prefix = f"{images_dirname}/"
    updated = re.sub(
        r'(\b(?:href|src)=["\'])\.\.\/(?:images|image)\/',
        rf"\g<1>{target_prefix}",
        updated,
        flags=re.IGNORECASE,
    )

    # 3. Clean any accidental double slashes or ./images
    updated = re.sub(
        r'(\b(?:href|src)=["\'])\.\/(?:images|image)\/',
        rf"\g<1>{target_prefix}",
        updated,
        flags=re.IGNORECASE,
    )

    return updated


def find_all_tag_bounds(html_text: str, tag_name: str, class_pattern: str) -> List[Tuple[int, int, int, int]]:
    """
    Finds all (start_pos, content_start, closing_start, closing_end) for matching tags,
    properly accounting for nested tags of the same type.
    """
    results = []
    pattern = re.compile(rf'<{tag_name}\b[^>]*class="[^"]*{class_pattern}[^"]*"[^>]*>', re.IGNORECASE)
    token_pattern = re.compile(rf'(<{tag_name}\b[^>]*>)|(</{tag_name}\s*>)', re.IGNORECASE)

    for m in pattern.finditer(html_text):
        start_pos = m.start()
        content_start = m.end()
        depth = 1
        for tok in token_pattern.finditer(html_text, content_start):
            if tok.group(1):
                depth += 1
            elif tok.group(2):
                depth -= 1
                if depth == 0:
                    results.append((start_pos, content_start, tok.start(), tok.end()))
                    break
    return results


def translate_post_text(
    inner_html: str,
    source_lang: str,
    target_lang: str,
    model: str,
    ollama_url: str,
) -> str:
    """
    Translates the messageText content of a post, protecting embedded images,
    attachment cards, and blockquotes.
    """
    # 1. Translate quote boxes separately if present and protect with placeholders
    quote_placeholders: Dict[str, str] = {}
    q_counter = 0

    def translate_quote_block(m):
        nonlocal q_counter
        full_quote = m.group(0)
        quote_attrs = m.group(1)
        quote_inner = m.group(2)
        clean_quote_text = html.unescape(re.sub(r"<[^>]+>", " ", quote_inner).strip())
        if clean_quote_text:
            trans_quote = query_ollama_translation(
                clean_quote_text,
                source_lang=source_lang,
                target_lang=target_lang,
                model=model,
                ollama_url=ollama_url,
            )
            trans_block = f'<blockquote{quote_attrs}><p>{html.escape(trans_quote)}</p></blockquote>'
        else:
            trans_block = full_quote
        q_key = f"___QUOTE_PLACEHOLDER_{q_counter}___"
        quote_placeholders[q_key] = trans_block
        q_counter += 1
        return f"\n{q_key}\n"

    processed = re.sub(
        r"<blockquote\b([^>]*)>(.*?)</blockquote>",
        translate_quote_block,
        inner_html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # 2. Extract and protect any image containers using placeholders
    placeholders: Dict[str, str] = {}
    ph_counter = 0

    def protect_images(m):
        nonlocal ph_counter
        key = f"___IMG_PLACEHOLDER_{ph_counter}___"
        placeholders[key] = m.group(0)
        ph_counter += 1
        return f"\n{key}\n"

    # Protect image preview divs
    processed = re.sub(
        r'<div\b[^>]*class=["\'][^"\']*attachmentImagePreview[^"\']*["\'][^>]*>.*?</div>',
        protect_images,
        processed,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Protect embedded image anchors
    processed = re.sub(
        r'<a\b[^>]*class=["\'][^"\']*embeddedImageLink[^"\']*["\'][^>]*>.*?</a>',
        protect_images,
        processed,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Protect attachment file cards
    processed = re.sub(
        r'<a\b[^>]*class=["\'][^"\']*messageAttachment[^"\']*["\'][^>]*>.*?</a>',
        protect_images,
        processed,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Protect any remaining <a> wrapping <img>
    processed = re.sub(
        r'<a\b[^>]*>((?:(?!</?a\b).)*?<img\b[^>]*>(?:(?!</?a\b).)*?)</a>',
        protect_images,
        processed,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Protect standalone <img> tags
    processed = re.sub(
        r"<img\b[^>]*>",
        protect_images,
        processed,
        flags=re.IGNORECASE,
    )

    # 3. Translate paragraphs / text lines
    p_pattern = re.compile(r"<p\b[^>]*>(.*?)</p>", re.DOTALL | re.IGNORECASE)

    if p_pattern.search(processed):
        def translate_p(m):
            p_content = m.group(1).strip()
            if re.match(r"^___IMG_PLACEHOLDER_\d+___$", p_content) or re.match(r"^___QUOTE_PLACEHOLDER_\d+___$", p_content):
                return m.group(0)
            clean_text = html.unescape(re.sub(r"<[^>]+>", " ", p_content).strip())
            if not clean_text:
                return m.group(0)
            trans_text = query_ollama_translation(
                clean_text,
                source_lang=source_lang,
                target_lang=target_lang,
                model=model,
                ollama_url=ollama_url,
            )
            return f"<p>{html.escape(trans_text)}</p>"

        translated_body = p_pattern.sub(translate_p, processed)
    else:
        # Fallback for plain text posts with <br>
        clean_text = html.unescape(re.sub(r"<br\s*/?>", "\n", processed))
        clean_text = re.sub(r"<[^>]+>", " ", clean_text).strip()
        if clean_text:
            trans_text = query_ollama_translation(
                clean_text,
                source_lang=source_lang,
                target_lang=target_lang,
                model=model,
                ollama_url=ollama_url,
            )
            translated_body = "".join(f"<p>{html.escape(line)}</p>" for line in trans_text.splitlines() if line.strip())
        else:
            translated_body = processed

    # 4. Restore protected image containers and quote boxes
    for key, original_tag in placeholders.items():
        translated_body = translated_body.replace(key, original_tag)
    for q_key, original_quote in quote_placeholders.items():
        translated_body = translated_body.replace(q_key, original_quote)

    return translated_body


def translate_thread_html(
    html_content: str,
    source_lang: str = "de",
    target_lang: str = "en",
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    images_dirname: str = "images",
) -> Tuple[str, str]:
    """
    Translates thread title and messageText in the HTML document,
    updating image links from '../images/' to 'images/'.
    Returns (translated_html, translated_title).
    """
    # 1. Update image links from '../images/' to 'images/'
    html_content = update_image_links_to_root(html_content, images_dirname=images_dirname)

    # 2. Translate thread title
    translated_title = "Translated Thread"
    title_m = re.search(r'<h1[^>]*class="[^"]*contentTitle[^"]*"[^>]*>(.*?)</h1>', html_content, re.DOTALL | re.IGNORECASE)
    if title_m:
        raw_title = html.unescape(re.sub(r"<[^>]+>", "", title_m.group(1)).strip())
        if raw_title:
            print(f"  Translating title: '{raw_title}'...")
            translated_title = query_ollama_translation(
                raw_title,
                source_lang=source_lang,
                target_lang=target_lang,
                model=model,
                ollama_url=ollama_url,
            )
            print(f"  -> '{translated_title}'")
            html_content = (
                html_content[: title_m.start(1)]
                + html.escape(translated_title)
                + html_content[title_m.end(1) :]
            )

    # Update document <title>
    html_content = re.sub(
        r"<title\b[^>]*>(.*?)</title>",
        rf"<title>{html.escape(translated_title)} ({target_lang.upper()})</title>",
        html_content,
        count=1,
        flags=re.IGNORECASE,
    )

    # 3. Translate each post's messageText
    bounds_list = find_all_tag_bounds(html_content, "div", "messageText")
    if not bounds_list:
        bounds_list = find_all_tag_bounds(html_content, "article", "message")

    print(f"  Translating {len(bounds_list)} post(s)...")

    # Replace from back to front to preserve string indices
    for start_pos, content_start, closing_start, closing_end in reversed(bounds_list):
        open_tag = html_content[start_pos:content_start]
        inner_body = html_content[content_start:closing_start]
        close_tag = html_content[closing_start:closing_end]

        translated_inner = translate_post_text(
            inner_body,
            source_lang=source_lang,
            target_lang=target_lang,
            model=model,
            ollama_url=ollama_url,
        )

        html_content = (
            html_content[:start_pos]
            + open_tag
            + translated_inner
            + close_tag
            + html_content[closing_end:]
        )

    return html_content, translated_title


def translate_single_html_file(
    source_html_path: str,
    target_html_path: str,
    source_lang: str = "de",
    target_lang: str = "en",
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    force: bool = False,
    registry_path: Optional[str] = None,
    images_dirname: str = "images",
) -> Optional[str]:
    """
    Translates a single German HTML file and writes the translated English HTML file.
    Updates translation.json registry upon completion.
    """
    if not os.path.isfile(source_html_path):
        print(f"Error: Source file does not exist: {source_html_path}")
        return None

    if not force and os.path.isfile(target_html_path) and os.path.getsize(target_html_path) > 0:
        print(f"  [SKIPPED] Target file already exists: {target_html_path} (use --force to overwrite)")
        return target_html_path

    try:
        with open(source_html_path, "r", encoding="utf-8") as f:
            raw_html = f.read()
    except Exception as e:
        print(f"Error reading source HTML {source_html_path}: {e}")
        return None

    print(f"\nProcessing: {os.path.basename(source_html_path)}")
    print(f"  Source: {source_html_path}")
    print(f"  Target: {target_html_path}")

    translated_html, translated_title = translate_thread_html(
        html_content=raw_html,
        source_lang=source_lang,
        target_lang=target_lang,
        model=model,
        ollama_url=ollama_url,
        images_dirname=images_dirname,
    )

    os.makedirs(os.path.dirname(os.path.abspath(target_html_path)), exist_ok=True)
    try:
        with open(target_html_path, "w", encoding="utf-8") as f:
            f.write(translated_html)
        file_size_kb = os.path.getsize(target_html_path) // 1024
        print(f"  [SUCCESS] Created {target_html_path} ({file_size_kb} KB)")

        if registry_path:
            record_translation_in_registry(
                registry_path=registry_path,
                source_filename=source_html_path,
                translated_filename=target_html_path,
                translated_title=translated_title,
                model=model,
                source_lang=source_lang,
                target_lang=target_lang,
                status="completed",
            )
            print(f"  [REGISTRY] Recorded in {registry_path}")

        return target_html_path
    except Exception as e:
        print(f"Error saving translated HTML {target_html_path}: {e}")
        return None


def translate_forum_directory(
    forum_dir: str,
    source_lang: str = "de",
    target_lang: str = "en",
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    force: bool = False,
    resume: bool = True,
    images_dirname: str = "images",
    input_dir: Optional[str] = None,
) -> List[str]:
    """
    Translates all German HTML articles in <html_dir> into <forum_dir>/<slug>.html.
    Resumes where left off based on translate.json (or translation.json).
    """
    html_dir = os.path.abspath(input_dir) if input_dir else os.path.join(forum_dir, "html")
    registry_path = resolve_registry_path(forum_dir)

    if not os.path.isdir(html_dir):
        print(f"Error: German HTML directory not found: {html_dir}")
        return []

    reg = load_translation_registry(registry_path)
    completed_translations = reg.get("translations", {})
    last_file = reg.get("last_translated_file")

    html_files = sorted(f for f in os.listdir(html_dir) if f.lower().endswith(".html"))
    if not html_files:
        print(f"No HTML files found in {html_dir}.")
        return []

    # If resuming and not force, filter out completed files
    files_to_process = []
    for fname in html_files:
        target_path = os.path.join(forum_dir, fname)
        if not force and resume:
            if os.path.isfile(target_path) and os.path.getsize(target_path) > 0:
                continue
            if fname in completed_translations and completed_translations[fname].get("status") == "completed":
                continue
        files_to_process.append(fname)

    if last_file and not force and resume:
        print(f"Resume: Last translated file was '{last_file}'. Remaining to translate: {len(files_to_process)}/{len(html_files)}.")

    print(f"========================================================")
    print(f"Translating {len(files_to_process)} file(s) in {forum_dir}")
    print(f"Source: {html_dir} (Language: {get_language_name(source_lang)})")
    print(f"Target: {forum_dir} (Language: {get_language_name(target_lang)})")
    print(f"Model: {model} @ {ollama_url}")
    print(f"Registry: {registry_path}")
    print(f"========================================================")

    translated_paths: List[str] = []
    for idx, fname in enumerate(files_to_process, start=1):
        src_path = os.path.join(html_dir, fname)
        dst_path = os.path.join(forum_dir, fname)
        print(f"\n[{idx}/{len(files_to_process)}] Translating {fname}...")
        res = translate_single_html_file(
            source_html_path=src_path,
            target_html_path=dst_path,
            source_lang=source_lang,
            target_lang=target_lang,
            model=model,
            ollama_url=ollama_url,
            force=force,
            registry_path=registry_path,
            images_dirname=images_dirname,
        )
        if res:
            translated_paths.append(res)

    print(f"\nFinished! Successfully translated {len(translated_paths)}/{len(files_to_process)} file(s).")
    return translated_paths


def main():
    parser = argparse.ArgumentParser(
        description="Philaforum Pure HTML Translator (Ollama-powered German to English HTML translation)"
    )
    parser.add_argument(
        "--forum-dir",
        "-d",
        help="Forum directory containing /html and /images subdirectories",
    )
    parser.add_argument(
        "--file",
        "-f",
        help="Translate a single specific .html file",
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        help="Custom input directory of German HTML files (defaults to <forum-dir>/html)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        help="Custom output directory for translated HTML (defaults to <forum-dir>)",
    )
    parser.add_argument(
        "--source-lang",
        default="de",
        help="Source language code (default: de)",
    )
    parser.add_argument(
        "--target-lang",
        default="en",
        help="Target language code (default: en)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--ollama-url",
        default=DEFAULT_OLLAMA_URL,
        help=f"Ollama server API base URL (default: {DEFAULT_OLLAMA_URL})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-translation of files even if already translated",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not skip previously completed files from translation.json",
    )

    args = parser.parse_args()

    # Verify Ollama connectivity
    if not check_ollama_available(args.ollama_url):
        print(
            f"Error: Cannot reach Ollama at {args.ollama_url}.\n"
            f"Please ensure Ollama is running ('ollama serve') with model '{args.model}' installed."
        )
        sys.exit(1)

    if args.file:
        src = os.path.abspath(args.file)
        if args.output_dir:
            dst = os.path.join(os.path.abspath(args.output_dir), os.path.basename(src))
        elif args.forum_dir:
            dst = os.path.join(os.path.abspath(args.forum_dir), os.path.basename(src))
        else:
            # If source is in .../html/file.html, default destination is .../file.html
            parent = os.path.dirname(src)
            if os.path.basename(parent).lower() == "html":
                dst = os.path.join(os.path.dirname(parent), os.path.basename(src))
            else:
                dst = os.path.join(parent, f"en-{os.path.basename(src)}")

        forum_dir = os.path.dirname(dst)
        reg_path = resolve_registry_path(forum_dir)
        translate_single_html_file(
            source_html_path=src,
            target_html_path=dst,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            model=args.model,
            ollama_url=args.ollama_url,
            force=args.force,
            registry_path=reg_path,
        )
    else:
        target_dir = args.forum_dir or args.output_dir or "."
        translate_forum_directory(
            forum_dir=os.path.abspath(target_dir),
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            model=args.model,
            ollama_url=args.ollama_url,
            force=args.force,
            resume=not args.no_resume,
            input_dir=args.input_dir,
        )


if __name__ == "__main__":
    main()
