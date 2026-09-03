#!/usr/bin/env python3
"""
Script to create a git tag based on the version in pom.xml and push tags to origin.

Usage:
  python build-tools/create_git_tag.py
  python build-tools/create_git_tag.py --no-push
"""

import sys
import re
import subprocess
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

def has_uncommitted_changes(repo_root: Path) -> bool:
    res = subprocess.run(["git", "status", "--porcelain"], cwd=str(repo_root), capture_output=True, text=True)
    return bool(res.stdout and res.stdout.strip())

def create_git_tag(repo_root: Path, version: str, push: bool = True) -> bool:
    if has_uncommitted_changes(repo_root):
        print("Error: Cannot create tag because there are uncommitted changes in the repository.")
        print("Please commit or stash your changes before creating a tag.")
        return False

    tag_name = f"v{version}"
    tag_msg = f"Created tag {tag_name}"

    tag_cmd = ["git", "tag", "-a", tag_name, "-m", tag_msg]
    print(f"Executing: {' '.join(tag_cmd)}")
    res = subprocess.run(tag_cmd, cwd=str(repo_root), capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error creating tag {tag_name}: {res.stderr.strip()}")
        return False
    print(f"Successfully created local tag: {tag_name}")

    if push:
        push_cmd = ["git", "push", "origin", "--tags"]
        print(f"Executing: {' '.join(push_cmd)}")
        res_push = subprocess.run(push_cmd, cwd=str(repo_root), capture_output=True, text=True)
        if res_push.returncode != 0:
            print(f"Error pushing tags to origin: {res_push.stderr.strip()}")
            return False
        print("Successfully pushed tags to origin")

    return True

def main():
    parser = argparse.ArgumentParser(description="Create git tag from pom.xml version and push tags to origin")
    parser.add_argument("--no-push", action="store_true", help="Create local tag without pushing to origin")
    args = parser.parse_args()

    repo_root = get_repo_root()
    pom_path = repo_root / "pom.xml"

    version = get_current_version(pom_path)
    should_push = not args.no_push

    success = create_git_tag(repo_root, version, push=should_push)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
