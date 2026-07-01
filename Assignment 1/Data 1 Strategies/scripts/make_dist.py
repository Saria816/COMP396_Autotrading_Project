#!/usr/bin/env python3
"""
make_dist.py
-------------
Create a clean ZIP archive of the BT396 project for distribution, excluding
editor/VCS metadata and Python bytecode caches.

Excluded by default:
  - .git/ (Git repository data)
  - .idea/ (JetBrains IDE project files)
  - __pycache__/ (Python bytecode caches)
  - .pytest_cache/, .mypy_cache/
  - .DS_Store (macOS)
  - Thumbs.db (Windows)

Optionally exclude the output/ folder (recommended) via --no-output to keep
ZIP small and avoid bundling generated images/json.

Usage (run from project root or anywhere):
  python scripts/make_dist.py                # produces BT396-dist.zip in project root
  python scripts/make_dist.py --no-output    # also exclude the output/ folder
  python scripts/make_dist.py --name BT396_0.1.0_win.zip
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import zipfile

EXCLUDE_DIRS = {
    '.git',
    '.idea',
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
}
EXCLUDE_FILES = {
    '.DS_Store',
    'Thumbs.db',
}

PROJECT_ROOT_SENTINELS = {
    'main.py',
    'framework',
    'strategies',
}

def is_under(path: Path, ancestor: Path) -> bool:
    try:
        path.relative_to(ancestor)
        return True
    except Exception:
        return False

def should_skip(path: Path, exclude_output: bool, root: Path) -> bool:
    # Skip excluded directories
    parts = set(p.name for p in path.parents)
    if parts & EXCLUDE_DIRS:
        return True
    # Skip excluded files by name
    if path.name in EXCLUDE_FILES:
        return True
    # Optionally skip output folder content
    if exclude_output:
        out_dir = root / 'output'
        if path.is_dir():
            if path.name == 'output' and path.parent == root:
                return True
        else:
            if is_under(path, out_dir):
                return True
    return False

def find_project_root(start: Path) -> Path:
    # Heuristic: look upward for folder containing main.py and framework/
    cur = start.resolve()
    for _ in range(5):  # search up to 5 levels above
        if (cur / 'main.py').exists() and (cur / 'framework').is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()

def make_zip(zip_name: str | None = None, exclude_output: bool = False):
    cwd = Path.cwd()
    root = find_project_root(cwd)
    if zip_name is None:
        zip_name = 'BT396-dist.zip'
    zip_path = root / zip_name

    # Build a file list
    files: list[Path] = []
    for p in root.rglob('*'):
        # Skip directories handled by should_skip
        if p.is_dir():
            # If the dir itself should be dropped, continue (children will be naturally skipped)
            if should_skip(p, exclude_output=exclude_output, root=root):
                continue
            else:
                continue  # directories are not added directly to zip; only files
        # Files
        if should_skip(p, exclude_output=exclude_output, root=root):
            continue
        files.append(p)

    # Write zip with relative paths from root
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for fp in files:
            arcname = str(fp.relative_to(root)).replace('\\', '/')
            zf.write(fp, arcname)

    print(f"Created: {zip_path}")
    print("Excluded directories:", ", ".join(sorted(EXCLUDE_DIRS)))
    if exclude_output:
        print("Also excluded: output/")


def main():
    ap = argparse.ArgumentParser(description='Create a clean distribution ZIP for BT396.')
    ap.add_argument('--name', help='Output zip file name (default: BT396-dist.zip)')
    ap.add_argument('--no-output', action='store_true', help='Exclude the output/ folder from the archive')
    args = ap.parse_args()
    make_zip(zip_name=args.name, exclude_output=args.no_output)

if __name__ == '__main__':
    main()
