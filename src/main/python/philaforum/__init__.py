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
Philaforum Package
Pure HTML scraper and Ollama-powered translation toolset for philaforum.com.
"""

__version__ = "1.0.0"

from .cleanup import (
    clean_directory,
    clean_html_file,
    clean_modification_log_entries,
    find_modification_log_entries,
    fix_blockquote_display,
)
from .scraper import (
    combine_thread_pages,
    embed_and_link_images,
    extract_thread_posts,
    extract_threads_from_board,
    fetch_and_save_image,
    fetch_url,
    sanitize_thread_html,
    scrape_board,
    scrape_thread,
)
