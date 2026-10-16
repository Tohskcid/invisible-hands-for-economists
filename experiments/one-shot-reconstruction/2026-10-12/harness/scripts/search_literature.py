#!/usr/bin/env python3
"""Fetch current literature metadata from Crossref and save auditable raw responses."""

import argparse
import datetime as dt
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path


def clean(value: object) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    return re.sub(r"<[^>]+>", "", value).strip() if isinstance(value, str) else ""


def year(item: dict) -> int | None:
    for key in ("published-print", "published-online", "issued"):
        parts = item.get(key, {}).get("date-parts", [])
        if parts and parts[0] and isinstance(parts[0][0], int):
            return parts[0][0]
    return None


def normalize(item: dict) -> dict:
    doi = clean(item.get("DOI"))
    return {
        "title": clean(item.get("title")),
        "authors": [
            " ".join(part for part in (clean(author.get("given")), clean(author.get("family"))) if part)
            for author in item.get("author", [])
            if isinstance(author, dict)
        ],
        "year": year(item),
        "venue": clean(item.get("container-title")),
        "doi": doi,
        "canonical_locator": f"https://doi.org/{doi}" if doi else clean(item.get("URL")),
        "type": clean(item.get("type")),
        "citation_count": item.get("is-referenced-by-count"),
        "abstract": clean(item.get("abstract")),
    }


def fetch(query: str, rows: int, user_agent: str) -> tuple[str, bytes, list[dict]]:
    params = urllib.parse.urlencode({"query.bibliographic": query, "rows": rows})
    url = f"https://api.crossref.org/works?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    payload = json.loads(raw)
    items = payload.get("message", {}).get("items", [])
    return url, raw, [normalize(item) for item in items if isinstance(item, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", action="append", required=True, help="repeat for each search formulation")
    parser.add_argument("--out", type=Path, required=True, help="combined evidence JSON path")
    parser.add_argument("--rows", type=int, default=20)
    parser.add_argument("--mailto", help="contact address for the Crossref polite pool")
    args = parser.parse_args()
    if not 1 <= args.rows <= 100:
        parser.error("--rows must be between 1 and 100")

    retrieved_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    user_agent = "invisible-hands-for-economists/2.17"
    if args.mailto:
        user_agent += f" (mailto:{args.mailto})"
    raw_dir = args.out.parent / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    searches, sources = [], []
    for query in args.query:
        url, raw, works = fetch(query, args.rows, user_agent)
        digest = hashlib.sha256(raw).hexdigest()
        raw_path = raw_dir / f"crossref-{digest[:16]}.json"
        raw_path.write_bytes(raw)
        searches.append({
            "source": "Crossref",
            "query": query,
            "retrieved_at": retrieved_at[:10],
            "retrieval_tool": "scripts/search_literature.py",
            "endpoint": url,
            "raw_artifact": raw_path.as_posix(),
            "raw_sha256": digest,
        })
        for work in works:
            work.update({"retrieval_tool": "scripts/search_literature.py", "retrieved_at": retrieved_at[:10]})
            sources.append(work)

    artifact = {
        "schema_version": "1",
        "generated_by": "scripts/search_literature.py",
        "retrieved_at": retrieved_at,
        "searches": searches,
        "sources": sources,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(args.out), "searches": len(searches), "sources": len(sources)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
