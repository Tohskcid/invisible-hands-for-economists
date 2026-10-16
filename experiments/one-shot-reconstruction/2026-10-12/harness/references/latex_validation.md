# LaTeX compilation and visual validation

Read this reference whenever a manuscript deliverable includes `.tex` or a PDF built from LaTeX. A source review is not sufficient: final delivery requires both deterministic compilation gates and inspection of rendered pages.

Preserve the project's document class, build system, engine, bibliography tool, fonts, and journal or university template. Do not install TeX, rewrite the preamble, or switch engines merely to silence an error without authorization. Prefer splitting or redesigning a wide table, calibrated columns, `tabularx`, `longtable`, or a landscape float; use `\resizebox` only as a last resort because it can make text unreadable.

## Typography, hyperlinks, and ink color

Academic publication standards require formal pure black body text. Do not configure `hyperref` with colored link text (`colorlinks=true` with colored fonts such as `darkblue` or `blue`), as dense in-text citations (`\citep`, `\citet`), internal cross-references (`\ref`, `\eqref`), and table of contents entries will turn paragraphs visibly blue.

Instead, always load `hyperref` with `[hidelinks]` and configure:

```latex
\usepackage[hidelinks]{hyperref}
\hypersetup{
    hidelinks,
    colorlinks=false,
    pdfborder={0 0 0}
}
```

This preserves full interactive PDF hyperlinks, section jumping, and metadata without introducing colored link boxes or non-black citation text.

## Long equations

No mathematical ink or equation number may cross the text block or enter either margin. Convert an overlong inline expression to display math. For display equations, break at meaningful relations or additive operators with `align`, `aligned`, `split`, or `multline`; indent continuation lines and preserve the intended equation numbering with `\notag` only where appropriate. When automatic delimiter sizing prevents a safe break, use explicit `\bigl`/`\bigr`-style delimiters around the relevant line segments.

Do not hide an overlong equation with `\resizebox`, `\scalebox`, `\scriptsize`, negative spacing, a smaller global math font, or a relaxed overfull threshold. Refactor notation or introduce a defined intermediate expression when semantic line breaks are still unreadable. The default zero-overfull gate must pass, and the page reviewer must confirm that every formula, delimiter, annotation, and equation number remains visibly inside the margins without overlap or clipping.

Run the harness in a build directory outside the source tree:

```bash
python3 scripts/check_latex.py check \
  --main paper/main.tex \
  --build-dir research/latex-build \
  --render-dir research/latex-pages \
  --report research/latex-report.json
```

Specify `--engine` when the project does not declare one and auto-detection would choose incorrectly. The harness does not install missing engines. It fails on compiler errors, missing files, undefined commands, unresolved citations or references, rerun requests that remain after compilation, any overfull box by default, missing/empty PDF, PDF metadata failure, rendering failure, or a rendered page-count mismatch. Do not raise `--overfull-limit` to waive a long equation. Underfull boxes remain warnings that require inspection.

Automated success is not delivery approval. Inspect every rendered page image, with special attention to tables, figures, equation line breaks and numbers, captions, footnotes, bibliography, appendices, rotated pages, headers/footers, glyphs, clipping, overlap, font size, margins, and page transitions. Record defects and rerun the full compile-and-render cycle after each material fix. `delivery_ready` remains false in the machine report because the script cannot prove visual readability.

After review, save only a compact record rather than image descriptions or page contents:

```json
{"pdf_sha256":"REPORT_HASH","status":"pass","reviewer":"layout-agent","pages_reviewed":[1,2],"issues":[]}
```

Bind that record to the exact compiled PDF:

```bash
python3 scripts/check_latex.py finalize \
  --report research/latex-report.json \
  --visual-review research/latex-visual-review.json \
  --output research/latex-final.json
```

Any hash mismatch, omitted or duplicate page, non-passing status, or unresolved issue keeps delivery blocked. Do not put page images or full compiler logs into the agent handoff; retain them as artifacts and return only status, defects, hashes, and paths.

For multi-agent work, assign a fresh typesetting reviewer the PDF pages and report, not the author's claimed success. The PI may deliver only after the automated gate passes and the reviewer confirms all pages inspected with zero material visual defects. Preserve the report and rendered-page paths as artifacts; do not commit generated PDFs or page images unless the project already does so.
