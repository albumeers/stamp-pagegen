#!/usr/bin/env python3
"""
Script to generate release notes between two git tags or commits.

Usage:
  python build-tools/generate_release_notes.py v2.6.3 v2.6.5
  python build-tools/generate_release_notes.py --from v2.6.3 --to v2.6.5
  python build-tools/generate_release_notes.py 2.6.3 2.6.5
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

def format_tag_name(tag: str) -> str:
    tag = tag.strip()
    if tag.upper() == "HEAD":
        return "HEAD"
    if not tag.startswith("v") and re.match(r"^\d+\.\d+\.\d+", tag):
        return f"v{tag}"
    return tag

def get_git_commits(repo_root: Path, from_tag: str, to_tag: str) -> list:
    rev_range = f"{from_tag}..{to_tag}"
    cmd = ["git", "log", rev_range, "--oneline"]
    res = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    if res.returncode != 0:
        # Fallback: try git log directly if range is not recognized
        cmd_all = ["git", "log", "--oneline", "-n", "50"]
        res = subprocess.run(cmd_all, cwd=str(repo_root), capture_output=True, text=True)
        if res.returncode != 0:
            return []
    lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    return lines

def categorize_commit(message: str) -> str:
    msg_lower = message.lower()
    if any(kw in msg_lower for kw in ["feat", "add", "implement", "create", "support", "new"]):
        return "Features"
    elif any(kw in msg_lower for kw in ["fix", "bug", "resolve", "correct", "issue", "close", "prevent"]):
        return "Fixes"
    else:
        return "Refactoring & Maintenance"

def generate_release_notes_md(from_tag: str, to_tag: str, commits: list) -> str:
    features = []
    fixes = []
    maintenance = []

    for line in commits:
        parts = line.split(" ", 1)
        commit_hash = parts[0]
        msg = parts[1] if len(parts) > 1 else line

        category = categorize_commit(msg)
        item_str = f"- {msg} (`{commit_hash}`)"

        if category == "Features":
            features.append(item_str)
        elif category == "Fixes":
            fixes.append(item_str)
        else:
            maintenance.append(item_str)

    md_lines = [
        f"# Release Notes ({from_tag} -> {to_tag})",
        ""
    ]

    if features:
        md_lines.append("## 🚀 Features")
        md_lines.extend(features)
        md_lines.append("")

    if fixes:
        md_lines.append("## 🐛 Fixes")
        md_lines.extend(fixes)
        md_lines.append("")

    if maintenance:
        md_lines.append("## 🔧 Refactoring & Maintenance")
        md_lines.extend(maintenance)
        md_lines.append("")

    if not features and not fixes and not maintenance:
        md_lines.append("No commits found in range.")
        md_lines.append("")

    return "\n".join(md_lines)

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Generate release notes between two git tags")
    parser.add_argument("from_tag", help="From tag/commit (e.g. v2.6.3 or 2.6.3)")
    parser.add_argument("to_tag", help="To tag/commit (e.g. v2.6.5 or 2.6.5)")

    args = parser.parse_args()

    repo_root = get_repo_root()
    from_tag = format_tag_name(args.from_tag)
    to_tag = format_tag_name(args.to_tag)

    commits = get_git_commits(repo_root, from_tag, to_tag)
    notes_md = generate_release_notes_md(from_tag, to_tag, commits)

    print(notes_md)

if __name__ == "__main__":
    main()
