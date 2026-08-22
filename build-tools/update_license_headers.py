#!/usr/bin/env python3
"""
Script to update or add license headers to all .java files in src/ and src/test/.

Rules:
1. For files without a copyright header, read licenseheader.txt from repo root.
   - Use git commit history to determine the earliest commit year of the file.
   - Generate date string as '<start_year>-<current_year>' (e.g. '2021-2026') or '<current_year>' if same (e.g. '2026').
   - Insert the header at the top of the file.
2. For files with an existing copyright header, update the date string.
   - If existing copyright start year is 2021 and current year is 2026, format as '2021-2026'.
   - Retain start year and append/update current year.
"""

import os
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path

def get_repo_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent

def get_current_year() -> int:
    return datetime.now().year

def get_earliest_git_year(file_path: Path, repo_root: Path) -> int:
    """Find the earliest commit year for a given file via git log."""
    try:
        rel_path = file_path.relative_to(repo_root)
        cmd = [
            "git", "log", "--follow", "--format=%ad", "--date=format:%Y", "--reverse", str(rel_path)
        ]
        result = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
            if lines:
                return int(lines[0])
    except Exception as e:
        print(f"Warning: Could not get git history for {file_path}: {e}")
    return get_current_year()

def is_header_present(content: str) -> bool:
    """Check if file starts with a copyright block comment."""
    stripped = content.lstrip()
    if stripped.startswith("/*") and "Copyright" in stripped[:1000]:
        return True
    return False

def format_date_str(start_year: int, current_year: int) -> str:
    if start_year == current_year:
        return str(current_year)
    return f"{start_year}-{current_year}"

def process_file(file_path: Path, license_template: str, current_year: int, repo_root: Path) -> bool:
    """
    Process a single Java file. Returns True if modified.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

    copyright_pattern = re.compile(r"Copyright\s+(\d{4})(?:\s*-\s*\d{4})?", re.IGNORECASE)

    if is_header_present(content):
        # Update existing header date
        match = copyright_pattern.search(content[:1000])
        if match:
            start_year = int(match.group(1))
            new_date_str = format_date_str(start_year, current_year)
            old_copyright_str = match.group(0)
            new_copyright_str = f"Copyright {new_date_str}"
            if old_copyright_str != new_copyright_str:
                new_content = content[:1000].replace(old_copyright_str, new_copyright_str, 1) + content[1000:]
                file_path.write_text(new_content, encoding="utf-8")
                print(f"Updated header in {file_path.relative_to(repo_root)}: {old_copyright_str} -> {new_copyright_str}")
                return True
        return False
    else:
        # Add new header using licenseheader.txt template and git commit year
        start_year = get_earliest_git_year(file_path, repo_root)
        date_str = format_date_str(start_year, current_year)
        
        # Format template with calculated date string
        # licenseheader.txt has "Copyright 2026 Jason Drake..."
        header = copyright_pattern.sub(f"Copyright {date_str}", license_template, count=1)
        
        # Ensure header ends with newline
        if not header.endswith("\n"):
            header += "\n"

        new_content = header + content
        file_path.write_text(new_content, encoding="utf-8")
        print(f"Added header to {file_path.relative_to(repo_root)} (Copyright {date_str})")
        return True

def main():
    repo_root = get_repo_root()
    license_file = repo_root / "licenseheader.txt"

    if not license_file.exists():
        print(f"Error: License template not found at {license_file}")
        sys.exit(1)

    license_template = license_file.read_text(encoding="utf-8")
    current_year = get_current_year()

    search_dirs = [repo_root / "src"]
    
    modified_count = 0
    total_count = 0

    for search_dir in search_dirs:
        if not search_dir.exists():
            print(f"Directory {search_dir} does not exist, skipping.")
            continue

        for java_file in search_dir.rglob("*.java"):
            total_count += 1
            if process_file(java_file, license_template, current_year, repo_root):
                modified_count += 1

    print(f"\nFinished. Processed {total_count} files, modified {modified_count} files.")

if __name__ == "__main__":
    main()
