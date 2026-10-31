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
Utility package.
"""

import importlib.util
import os
import sys
from . import translate

translation = translate
sys.modules[__name__ + ".translation"] = translate

# Dynamically load split-pages
_split_pages_path = os.path.join(os.path.dirname(__file__), "split-pages.py")
if os.path.isfile(_split_pages_path):
    _spec = importlib.util.spec_from_file_location("util.split_pages", _split_pages_path)
    if _spec and _spec.loader:
        _split_mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_split_mod)
        sys.modules[__name__ + ".split_pages"] = _split_mod
        split_pages = _split_mod
