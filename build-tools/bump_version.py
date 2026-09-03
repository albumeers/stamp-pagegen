#!/usr/bin/env python3
"""
Script to bump version in pom.xml.

Usage:
  python build-tools/bump_version.py 2.6.4
  python build-tools/bump_version.py --version 2.6.4
  python build-tools/bump_version.py --patch
"""

import sys
import re
import argparse
from pathlib import Path

def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent

def get_current_version(pom_path: Path) -> str:
    if not pom_path.exists():
        raise FileNotFoundError(f"pom.xml not found at {pom_path}")
    content = pom_path.read_text(encoding="utf-8")
    match = re.search(r"<version>([^<]+)</version>", content)
    if not match:
        raise ValueError("Could not find <version> tag in pom.xml")
    return match.group(1)

def increment_patch_version(version_str: str) -> str:
    parts = version_str.split(".")
    if len(parts) >= 3 and parts[-1].isdigit():
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    raise ValueError(f"Version '{version_str}' is not in standard semver format (x.y.z)")

def bump_version(pom_path: Path, new_version: str) -> bool:
    if not pom_path.exists():
        raise FileNotFoundError(f"pom.xml not found at {pom_path}")
    content = pom_path.read_text(encoding="utf-8")
    
    # Replace the main project <version> tag (first occurrence in pom.xml)
    new_content, count = re.subn(r"(<version>)[^<]+(</version>)", rf"\g<1>{new_version}\g<2>", content, count=1)
    if count == 0:
        return False
        
    pom_path.write_text(new_content, encoding="utf-8")
    return True

def main():
    parser = argparse.ArgumentParser(description="Bump project version in pom.xml")
    parser.add_argument("target_version", nargs="?", help="New version string (e.g. 2.6.4)")
    parser.add_argument("--version", "-v", dest="flag_version", help="New version string (e.g. 2.6.4)")
    parser.add_argument("--patch", action="store_true", help="Auto-increment the patch version")

    args = parser.parse_args()

    repo_root = get_repo_root()
    pom_path = repo_root / "pom.xml"

    current_version = get_current_version(pom_path)

    new_version = args.target_version or args.flag_version
    if args.patch:
        new_version = increment_patch_version(current_version)
    elif not new_version:
        print(f"Current version: {current_version}")
        print("Error: Specify a version (e.g. 'python build-tools/bump_version.py 2.6.4' or '--patch')")
        sys.exit(1)

    if new_version == current_version:
        print(f"Version is already {current_version}. No changes made.")
        return

    if bump_version(pom_path, new_version):
        print(f"Updated pom.xml version: {current_version} -> {new_version}")
    else:
        print(f"Error: Failed to update version in {pom_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()
