#!/usr/bin/env python3
"""
Fix bad GitHub Pages paths in-place.

Normalizes root-absolute paths to:
  /<repo>/<...>

Also fixes accidental double-prefixing like:
  /<repo>/Cyb3Raya/...  -> /<repo>/...

And fixes older prefix:
  /Cyb3Raya/...         -> /<repo>/...

Creates .bak backups unless --no-backup.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ATTR_PATTERN = re.compile(
    r'''(?P<prefix>\b(?:href|src|action)\s*=\s*["'])
        (?P<path>[^"']*)
        (?P<suffix>["'])
    ''',
    re.IGNORECASE | re.VERBOSE,
)

CSS_URL_PATTERN = re.compile(
    r'''(?P<prefix>\burl\(\s*["']?)
        (?P<path>[^)"']*)
        (?P<suffix>["']?\s*\))
    ''',
    re.IGNORECASE | re.VERBOSE,
)


def is_external(url: str) -> bool:
    u = url.strip()
    low = u.lower()
    return (
        low.startswith("http://")
        or low.startswith("https://")
        or low.startswith("mailto:")
        or low.startswith("tel:")
        or low.startswith("data:")
        or low.startswith("javascript:")
        or low.startswith("//")
        or low.startswith("#")
    )


def normalize_root_path(path: str, repo: str) -> str:
    """
    Convert root-absolute paths to /<repo>/... and fix known bad prefixes.
    Only touches strings that start with "/".
    """
    p = path.strip()
    if not p.startswith("/"):
        return path  # not root-absolute, leave it alone
    if is_external(p):
        return path

    # If it already starts with the correct repo, keep it (but fix common double-prefix mistake)
    good = f"/{repo}"
    if p == good or p.startswith(good + "/"):
        # Fix accidental: /<repo>/Cyb3Raya/... -> /<repo>/...
        p = re.sub(rf"^/{re.escape(repo)}/Cyb3Raya(?=/|$)", f"/{repo}", p)
        return p

    # Fix older prefix: /Cyb3Raya/... -> /<repo>/...
    if p == "/Cyb3Raya" or p.startswith("/Cyb3Raya/"):
        remainder = p[len("/Cyb3Raya"):]  # includes leading "/" or empty
        if remainder == "":
            remainder = "/"
        return f"/{repo}{remainder}"

    # Any other root-absolute path like /CSS/... -> /<repo>/CSS/...
    return f"/{repo}{p}"


def rewrite_text(text: str, repo: str) -> tuple[str, int]:
    count = 0

    def repl_attr(m: re.Match) -> str:
        nonlocal count
        old = m.group("path")
        new = old
        if old.strip().startswith("/"):
            new = normalize_root_path(old, repo)
        if new != old:
            count += 1
        return f"{m.group('prefix')}{new}{m.group('suffix')}"

    def repl_css(m: re.Match) -> str:
        nonlocal count
        old = m.group("path")
        new = old
        if old.strip().startswith("/"):
            new = normalize_root_path(old, repo)
        if new != old:
            count += 1
        return f"{m.group('prefix')}{new}{m.group('suffix')}"

    out = ATTR_PATTERN.sub(repl_attr, text)
    out = CSS_URL_PATTERN.sub(repl_css, out)
    return out, count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Project root directory (default: .)")
    ap.add_argument("--repo", required=True, help="GitHub repo name, e.g. Cyb3Raya-Blog")
    ap.add_argument("--ext", default=".html,.css", help="Extensions to process (default: .html,.css)")
    ap.add_argument("--dry-run", action="store_true", help="Preview changes only")
    ap.add_argument("--no-backup", action="store_true", help="Disable .bak backups")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    repo = args.repo.strip("/")

    exts = [e.strip() for e in args.ext.split(",") if e.strip()]
    files: set[Path] = set()
    for ext in exts:
        files.update(root.rglob(f"*{ext}"))

    total_files = 0
    total_changes = 0

    for fp in sorted(files):
        if fp.name.endswith(".bak"):
            continue

        try:
            original = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"[skip] non-utf8: {fp}")
            continue

        updated, cnt = rewrite_text(original, repo)
        if cnt == 0:
            continue

        total_files += 1
        total_changes += cnt

        if args.dry_run:
            print(f"[dry-run] {fp} -> {cnt} fixes")
            continue

        if not args.no_backup:
            bak = fp.with_suffix(fp.suffix + ".bak")
            if not bak.exists():
                bak.write_text(original, encoding="utf-8")

        fp.write_text(updated, encoding="utf-8")
        print(f"[updated] {fp} -> {cnt} fixes")

    print(f"\nDone. Files changed: {total_files}, total fixes: {total_changes}")
    if args.dry_run:
        print("Dry-run only: no files were modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

