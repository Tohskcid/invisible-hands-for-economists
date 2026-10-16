# Research PDF ingestion

Use this reference for papers supplied only as PDF. Preserve the original file as the authority.

1. If MarkItDown is already available, use it for first-pass Markdown and navigation. Prefer local-only conversion (`convert_local()` in Python); do not install it without authorization. For formula-, table-, layout-, or OCR-heavy documents, use Docling instead only when it is already available or authorized; record which parser and version produced the artifact.
2. Build an index of headings, definitions, theorem labels, tables, appendices, and references from the Markdown.
3. Treat converted text as a locator, not evidence for mathematical content. Verify every equation, quantifier, assumption, theorem statement, table value, and proof-critical symbol against rendered source pages.
4. Record the source page and label beside each normalized transcription. Preserve uncertainty where reading order, subscripts, superscripts, symbols, or table structure are ambiguous.
5. For scanned pages, use OCR only when available and authorized, then apply the same visual check. Never silently repair a formula from context.

Keep the Markdown and page renders as artifacts rather than loading the entire paper into context. MarkItDown is optional; fall back to existing PDF extraction and rendering tools when unavailable.

For papers acquired as part of a bibliography rather than supplied by the user, also follow [project_layout.md](project_layout.md) for lawful acquisition, stable naming, checksums, and archive coverage.
