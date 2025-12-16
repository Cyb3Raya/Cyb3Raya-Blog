#!/usr/bin/env python3
"""
Mass-fix absolute paths after moving from:
  https://username.github.io/REPO/
to a custom domain:
  https://yourdomain.com/

Example fixes:
  /Cyb3Raya-Blog/CSS/style.css  -> /CSS/style.css
  /Cyb3Raya/HTML/blog.html      -> /HTML/blog.html

This script:
  - Recursively scans files under a chosen root directory
  - Replaces one or more "bad" path prefixes with "/"
  - Writes a .bak backup before modifying a file
  - Prints a summary of changes

Usage examples:
  python3 fix_paths.py --root "/path/to/site" --prefix "/Cyb3Raya-Blog/"
  python3 fix_paths.py --root . --prefix "/Cyb3Raya/" --prefix "/Cyb3Raya-Blog/" --dry-run
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable, List, Tuple


TEXT_EXTS = {
    ".html", ".htm",
    ".css",
    ".js", ".mjs",
    ".json", ".xml", ".txt",
    ".md",
    ".yml", ".yaml",
    ".svg",
}


def is_probably_text_file(path: Path) -> bool:
    """
    Heuristic: treat known text extensions as text. This avoids corrupting binaries.
    """
    return path.suffix.lower() in TEXT_EXTS


def load_text(path: Path) -> str:
    """
    Read as UTF-8, fall back to latin-1 if needed to avoid crashing.
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def save_text(path: Path, content: str) -> None:
    """
    Save as UTF-8 (most web projects are UTF-8). If that causes issues for a file,
    you can adjust this, but it is the most common and safest default.
    """
    path.write_text(content, encoding="utf-8")


def apply_replacements(content: str, bad_prefixes: Iterable[str]) -> Tuple[str, int]:
    """
    Replace each bad prefix with '/'.
    Returns (new_content, total_replacements_made)
    """
    total = 0
    new_content = content

    for prefix in bad_prefixes:
        if not prefix:
            continue

        # Normalize prefixes: ensure they start and end with '/'
        p = prefix
        if not p.startswith("/"):
            p = "/" + p
        if not p.endswith("/"):
            p = p + "/"

        # Replace occurrences of "/REPO/" with "/"
        # Example: href="/Cyb3Raya-Blog/CSS/style.css" -> href="/CSS/style.css"
        before = new_content
        new_content = new_content.replace(p, "/")

        # Count how many replacements happened for this prefix
        # Using difference in split count is a simple reliable measure.
        total += max(0, len(before.split(p)) - 1)

    return new_content, total


def should_skip_dir(path: Path) -> bool:
    """
    Skip common junk directories.
    """
    parts = {p.lower() for p in path.parts}
    return any(
        x in parts for x in {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix GitHub Pages repo-prefixed paths for custom domains.")
    parser.add_argument("--root", required=True, help="Root directory of your site/project.")
    parser.add_argument(
        "--prefix",
        action="append",
        default=[],
        help="Bad prefix to remove (repeatable). Example: /Cyb3Raya-Blog/ or /Cyb3Raya/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change, but do not modify files.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create .bak files (not recommended).",
    )

    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    bad_prefixes: List[str] = args.prefix

    if not root.exists() or not root.is_dir():
        print(f"Error: root path does not exist or is not a directory: {root}")
        return 2

    if not bad_prefixes:
        print("Error: you must provide at least one --prefix to remove.")
        print('Example: --prefix "/Cyb3Raya-Blog/"')
        return 2

    changed_files: List[Tuple[Path, int]] = []
    scanned = 0
    skipped = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dpath = Path(dirpath)

        if should_skip_dir(dpath):
            dirnames[:] = []
            continue

        for name in filenames:
            path = dpath / name

            if not is_probably_text_file(path):
                skipped += 1
                continue

            scanned += 1
            original = load_text(path)
            updated, count = apply_replacements(original, bad_prefixes)

            if count <= 0 or updated == original:
                continue

            if args.dry_run:
                print(f"Would change: {path} (replacements: {count})")
            else:
                if not args.no_backup:
                    backup_path = path.with_suffix(path.suffix + ".bak")
                    if not backup_path.exists():
                        backup_path.write_text(original, encoding="utf-8", errors="ignore")

                save_text(path, updated)
                print(f"Changed: {path} (replacements: {count})")

            changed_files.append((path, count))

    total_repls = sum(c for _, c in changed_files)

    print("")
    print("Summary")
    print(f"Root: {root}")
    print(f"Prefixes removed: {bad_prefixes}")
    print(f"Files scanned: {scanned}")
    print(f"Files skipped (non-text ext): {skipped}")
    print(f"Files changed: {len(changed_files)}")
    print(f"Total replacements: {total_repls}")

    if args.dry_run:
        print("")
        print("Dry-run mode: no files were modified.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

