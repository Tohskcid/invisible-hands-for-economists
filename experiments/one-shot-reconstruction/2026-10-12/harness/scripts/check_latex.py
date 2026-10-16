#!/usr/bin/env python3
"""Compile a LaTeX manuscript, reject deterministic defects, and render every page."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ENGINES = ("latexmk", "tectonic", "pdflatex", "xelatex", "lualatex")
MAGIC_ENGINE = re.compile(r"(?im)^\s*%\s*!\s*TeX\s+program\s*=\s*([A-Za-z0-9_-]+)")
OVERFULL = re.compile(r"Overfull \\[hv]box \(([0-9.]+)pt too (?:wide|high)\)", re.IGNORECASE)
FATAL_PATTERNS = (
    re.compile(r"(?:LaTeX|Package\s+\S+) Error:", re.IGNORECASE),
    re.compile(r"Undefined control sequence", re.IGNORECASE),
    re.compile(r"Emergency stop|Fatal error occurred", re.IGNORECASE),
    re.compile(r"File [`'].+?[`'] not found", re.IGNORECASE),
    re.compile(r"(?:Citation|Reference).+undefined", re.IGNORECASE),
    re.compile(r"There were undefined (?:references|citations)", re.IGNORECASE),
    re.compile(r"Please \(re\)run Biber|Please rerun LaTeX", re.IGNORECASE),
    re.compile(r"Label\(s\) may have changed", re.IGNORECASE),
    re.compile(r"Float too large for page|Too many unprocessed floats|Dimension too large", re.IGNORECASE),
)


def select_engine(main: Path, requested: str) -> str:
    if requested != "auto":
        if not shutil.which(requested):
            raise ValueError(f"requested LaTeX engine is unavailable: {requested}")
        return requested
    source = main.read_text(encoding="utf-8", errors="replace")[:4000]
    match = MAGIC_ENGINE.search(source)
    if match:
        named = {"pdftex": "pdflatex", "xetex": "xelatex", "luatex": "lualatex"}.get(match.group(1).lower(), match.group(1).lower())
        if named in ENGINES and shutil.which(named):
            return named
        raise ValueError(f"LaTeX magic comment requests unavailable engine: {named}")
    for engine in ENGINES:
        if shutil.which(engine):
            return engine
    raise ValueError("no supported LaTeX engine found; install one outside this skill run")


def engine_commands(engine: str, main: Path, build_dir: Path) -> list[list[str]]:
    output = str(build_dir.resolve())
    if engine == "latexmk":
        return [[engine, "-pdf", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", f"-outdir={output}", main.name]]
    if engine == "tectonic":
        return [[engine, "--only-cached", "--untrusted", "--keep-logs", "--keep-intermediates", "--outdir", output, main.name]]
    command = [engine, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "-no-shell-escape", "-recorder", f"-output-directory={output}", main.name]
    cmds = [command]
    if shutil.which("bibtex"):
        try:
            rel_aux = (build_dir / main.stem).resolve().relative_to(main.parent.resolve())
        except ValueError:
            rel_aux = build_dir / main.stem
        cmds.append(["bibtex", str(rel_aux)])
        cmds.append(command)
    cmds.append(command)
    return cmds


def analyze_log(text: str, overfull_limit: float) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    for pattern in FATAL_PATTERNS:
        if pattern.search(text):
            errors.append(f"log matches fatal pattern: {pattern.pattern}")
    for match in OVERFULL.finditer(text):
        amount = float(match.group(1))
        message = f"overfull box exceeds margin by {amount:g}pt"
        (errors if amount > overfull_limit else warnings).append(message)
    if re.search(r"Underfull \\[hv]box", text, re.IGNORECASE):
        warnings.append("underfull box reported; inspect typography")
    return sorted(set(errors)), sorted(set(warnings))


def compile_tex(main: Path, build_dir: Path, engine: str, timeout: int, overfull_limit: float) -> dict:
    build_dir.mkdir(parents=True, exist_ok=True)
    final_output, command_errors = "", []
    commands = engine_commands(engine, main, build_dir)
    for command in commands:
        try:
            completed = subprocess.run(
                command,
                cwd=main.parent,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"engine": engine, "commands": commands, "errors": ["LaTeX compilation timed out"], "warnings": [], "pdf": None}
        final_output = "\n".join([completed.stdout, completed.stderr])
        if completed.returncode:
            command_errors.append(f"compiler exit code: {completed.returncode}")
            break
    log_path = build_dir / f"{main.stem}.log"
    if log_path.is_file():
        final_output += "\n" + log_path.read_text(encoding="utf-8", errors="replace")
    errors, warnings = analyze_log(final_output, overfull_limit)
    errors.extend(command_errors)
    pdf = build_dir / f"{main.stem}.pdf"
    if not pdf.is_file() or pdf.stat().st_size == 0:
        errors.append("compiler did not produce a non-empty PDF")
    return {
        "engine": engine,
        "commands": commands,
        "errors": sorted(set(errors)),
        "warnings": warnings,
        "pdf": str(pdf) if pdf.is_file() else None,
    }


def render_pdf(pdf: Path, render_dir: Path, timeout: int) -> dict:
    renderer, info_tool = shutil.which("pdftoppm"), shutil.which("pdfinfo")
    if not renderer or not info_tool:
        return {"errors": ["pdftoppm and pdfinfo are required for visual QA"], "pages": [], "page_count": None}
    render_dir.mkdir(parents=True, exist_ok=True)
    for stale in render_dir.glob("page-*.png"):
        stale.unlink()
    try:
        info = subprocess.run([info_tool, str(pdf)], capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"errors": ["PDF inspection or rendering timed out"], "pages": [], "page_count": None}
    errors = []
    if info.returncode:
        errors.append(f"pdfinfo failed: {info.stderr.strip()}")
    match = re.search(r"(?m)^Pages:\s+(\d+)", info.stdout)
    page_count = int(match.group(1)) if match else None
    size_match = re.search(r"(?m)^Page size:\s+(.+)$", info.stdout)
    if page_count is None:
        errors.append("pdfinfo did not report a page count")
    if page_count is not None:
        for page in range(1, page_count + 1):
            prefix = render_dir / f"page-{page:04d}"
            try:
                rendered = subprocess.run(
                    [renderer, "-png", "-r", "150", "-f", str(page), "-l", str(page), "-singlefile", str(pdf), str(prefix)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                errors.append(f"rendering page {page} timed out")
                break
            if rendered.returncode:
                errors.append(f"pdftoppm failed on page {page}: {rendered.stderr.strip()}")
                break
    pages = sorted(str(path) for path in render_dir.glob("page-*.png"))
    if not pages:
        errors.append("renderer produced no page images")
    if page_count is not None and len(pages) != page_count:
        errors.append(f"rendered {len(pages)} pages but PDF reports {page_count}")
    text_tool = shutil.which("pdftotext")
    if text_tool:
        try:
            extracted = subprocess.run([text_tool, str(pdf), "-"], capture_output=True, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            errors.append("PDF text extraction timed out")
        else:
            if extracted.returncode == 0 and "??" in extracted.stdout:
                errors.append("rendered PDF text contains unresolved ?? token")
    return {
        "errors": errors,
        "pages": pages,
        "page_count": page_count,
        "page_size": size_match.group(1).strip() if size_match else None,
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
    }


def check(main: Path, build_dir: Path, render_dir: Path, requested_engine: str, timeout: int, overfull_limit: float) -> dict:
    if not main.is_file() or main.suffix.casefold() != ".tex":
        raise ValueError("main must be an existing .tex file")
    if "\\documentclass" not in main.read_text(encoding="utf-8", errors="replace"):
        raise ValueError("main must be a complete document containing \\documentclass")
    if build_dir.resolve() == main.parent.resolve():
        raise ValueError("build-dir must be separate from the source directory")
    engine = select_engine(main, requested_engine)
    compilation = compile_tex(main.resolve(), build_dir.resolve(), engine, timeout, overfull_limit)
    rendering = {"errors": ["render skipped because compilation failed"], "pages": [], "page_count": None}
    if not compilation["errors"] and compilation["pdf"]:
        rendering = render_pdf(Path(compilation["pdf"]), render_dir.resolve(), timeout)
    automated_passed = not compilation["errors"] and not rendering["errors"]
    return {
        "automated_passed": automated_passed,
        "delivery_ready": False,
        "visual_review_required": automated_passed,
        "compilation": compilation,
        "rendering": rendering,
        "note": "delivery_ready remains false until an agent or researcher visually inspects every rendered page",
    }


def finalize(report: dict, review: dict) -> dict:
    """Bind a human/agent page review to the exact PDF produced by the gate."""
    errors = []
    rendering = report.get("rendering", {})
    if not report.get("automated_passed"):
        errors.append("automated LaTeX gate did not pass")
    if review.get("pdf_sha256") != rendering.get("pdf_sha256"):
        errors.append("visual review PDF hash does not match the compiled PDF")
    if review.get("status") != "pass":
        errors.append("visual review status must be pass")
    if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
        errors.append("visual review requires a reviewer identifier")
    page_count = rendering.get("page_count")
    expected = set(range(1, page_count + 1)) if isinstance(page_count, int) else set()
    pages = review.get("pages_reviewed")
    if not isinstance(pages, list) or any(isinstance(page, bool) or not isinstance(page, int) for page in pages):
        errors.append("pages_reviewed must be a list of page numbers")
    elif set(pages) != expected or len(pages) != len(expected):
        errors.append("visual review must cover every PDF page exactly once")
    issues = review.get("issues")
    if not isinstance(issues, list):
        errors.append("issues must be a list")
    elif issues:
        errors.append("visual review contains unresolved issues")
    return {
        "delivery_ready": not errors,
        "errors": errors,
        "pdf_sha256": rendering.get("pdf_sha256"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check_parser = subparsers.add_parser("check", help="compile, inspect logs, and render every page")
    check_parser.add_argument("--main", type=Path, required=True)
    check_parser.add_argument("--build-dir", type=Path, required=True)
    check_parser.add_argument("--render-dir", type=Path)
    check_parser.add_argument("--engine", choices=("auto", *ENGINES), default="auto")
    check_parser.add_argument("--timeout", type=int, default=180)
    check_parser.add_argument("--overfull-limit", type=float, default=0.0)
    check_parser.add_argument("--report", type=Path)
    finalize_parser = subparsers.add_parser("finalize", help="bind visual review to an automated report")
    finalize_parser.add_argument("--report", type=Path, required=True)
    finalize_parser.add_argument("--visual-review", type=Path, required=True)
    finalize_parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "finalize":
        try:
            report = json.loads(args.report.read_text(encoding="utf-8"))
            review = json.loads(args.visual_review.read_text(encoding="utf-8"))
            result = finalize(report, review)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[Error] Cannot finalize LaTeX review: {exc}", file=sys.stderr)
            return 2
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 0 if result["delivery_ready"] else 1
    if args.timeout <= 0 or args.overfull_limit < 0:
        print("[Error] timeout must be positive and overfull-limit nonnegative", file=sys.stderr)
        return 2
    try:
        result = check(
            args.main,
            args.build_dir,
            args.render_dir or args.build_dir / "rendered",
            args.engine,
            args.timeout,
            args.overfull_limit,
        )
    except (OSError, ValueError) as exc:
        print(f"[Error] Cannot validate LaTeX manuscript: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["automated_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
