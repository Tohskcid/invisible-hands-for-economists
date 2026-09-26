#!/usr/bin/env python3
"""Reject uncategorized paper artifacts and leaked build files."""

import argparse
import json
import os
import sys
from pathlib import Path


SKIP_DIRS = {".agents", ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
DISPOSABLE_DIRS = {"build", "tmp", "temp", "scratch", ".cache", "rendered_pages", "latex-build"}
LATEX_TEMP = {".aux", ".bbl", ".bcf", ".blg", ".fdb_latexmk", ".fls", ".log", ".nav", ".out", ".run.xml", ".snm", ".synctex.gz", ".toc", ".xdv"}

CATEGORIES = {
    "manuscript": {
        "extensions": {".tex", ".bib", ".pdf", ".doc", ".docx", ".odt", ".rtf", ".html"},
        "directories": {"paper", "papers", "manuscript", "manuscripts", "docs", "documents", "latex", "literature", "output", "outputs", "reports", "research", "scripts", "src"},
    },
    "figure": {
        "extensions": {".png", ".jpg", ".jpeg", ".svg", ".eps", ".tif", ".tiff", ".webp"},
        "directories": {"figure", "figures", "image", "images", "plot", "plots", "assets", "output", "outputs", "paper", "docs", "latex", "literature", "scratch"},
    },
    "data/result": {
        "extensions": {".csv", ".tsv", ".parquet", ".feather", ".dta", ".sav", ".xls", ".xlsx", ".sqlite", ".db", ".jsonl"},
        "directories": {"data", "dataset", "datasets", "table", "tables", "result", "results", "output", "outputs", "research", "literature", "library", "evals", "fixtures", "scratch"},
    },
    "code/notebook": {
        "extensions": {".py", ".r", ".jl", ".do", ".ipynb"},
        "directories": {"script", "scripts", "src", "source", "code", "notebook", "notebooks", "analysis", "tests", "scratch"},
    },
    "archive": {
        "extensions": {".zip", ".tar", ".gz", ".7z"},
        "directories": {"archive", "archives", "release", "releases", "output", "outputs", "paper", "docs", "literature", "research", "scratch"},
    },
}


def suffix(path: Path) -> str:
    name = path.name.lower()
    for compound in (".synctex.gz", ".run.xml"):
        if name.endswith(compound):
            return compound
    return path.suffix.lower()


def directory_names(path: Path, root: Path) -> set[str]:
    return {part.lower() for part in path.relative_to(root).parts[:-1]}


def scan(root: Path) -> dict:
    violations: list[dict[str, str]] = []
    checked = 0
    for current, directories, filenames in os.walk(root):
        directories[:] = sorted(name for name in directories if name not in SKIP_DIRS)
        current_path = Path(current)
        for filename in sorted(filenames):
            path = current_path / filename
            if path.is_symlink():
                continue
            checked += 1
            relative = path.relative_to(root).as_posix()
            extension = suffix(path)
            parents = directory_names(path, root)

            if extension in LATEX_TEMP and not (parents & DISPOSABLE_DIRS):
                violations.append({
                    "path": relative,
                    "kind": "latex-build-artifact",
                    "message": "move compilation output to an ignored build/temp directory",
                })
                continue

            if parents & DISPOSABLE_DIRS:
                continue

            for category, rule in CATEGORIES.items():
                if extension not in rule["extensions"]:
                    continue
                if not (parents & rule["directories"]):
                    violations.append({
                        "path": relative,
                        "kind": "uncategorized-artifact",
                        "message": f"place {category} files in a purpose-named folder",
                    })
                break

    return {
        "valid": not violations,
        "iteration_required": bool(violations),
        "return_to": [] if not violations else ["artifact_organization"],
        "root": str(root),
        "files_checked": checked,
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"[Error] Directory not found: {root}", file=sys.stderr)
        return 2
    report = scan(root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["valid"]:
        print(f"[OK] {report['files_checked']} files are organized by purpose")
    else:
        for item in report["violations"]:
            print(f"[FAIL] {item['path']}: {item['message']}")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
