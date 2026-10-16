#!/usr/bin/env python3
"""Search the bundled economics result-card library."""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HIDDEN_IN_BLIND_MODE = {"Proof strategy", "Solution outline", "Author proof locator"}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def words(value) -> list[str]:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    normalized = unicodedata.normalize("NFKD", str(value)).casefold()
    return re.findall(r"[\w]+", normalized)


def score(card: dict, query: str) -> int:
    query_words = words(query)
    if not query_words:
        return 0
    weighted_fields = {
        "keywords": 5,
        "problem": 4,
        "title": 3,
        "method": 1,
    }
    total = 0
    for field, weight in weighted_fields.items():
        field_words = set(words(card.get(field, "")))
        total += weight * sum(token in field_words for token in query_words)
    phrase = " ".join(query_words)
    haystack = " ".join(words([card.get(field, "") for field in weighted_fields]))
    if phrase and phrase in haystack:
        total += 3
    return total


def search(cards: list[dict], query: str, mode: str | None, result_type: str | None, limit: int, blind: bool) -> list[dict]:
    matches = []
    for card in cards:
        if mode and card.get("mode") != mode:
            continue
        if result_type and card.get("result_type") != result_type:
            continue
        relevance = score(card, query)
        if relevance <= 0:
            continue
        visible = dict(card)
        visible["score"] = relevance
        matches.append(visible)
    return sorted(matches, key=lambda item: (-item["score"], item["id"]))[:limit]


def hide_solution_sections(markdown: str) -> str:
    """Remove author-solution sections while retaining the result statement."""
    output, hidden = [], False
    for line in markdown.splitlines():
        if line.startswith("## "):
            hidden = line[3:].strip() in HIDDEN_IN_BLIND_MODE
        if not hidden:
            output.append(line)
    return "\n".join(output).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?")
    parser.add_argument("--mode", choices=["theory", "empirical", "structural"])
    parser.add_argument("--type", dest="result_type")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--blind", action="store_true", help="hide proof and solution fields")
    parser.add_argument("--show", metavar="CARD_ID", help="print one selected Markdown card")
    parser.add_argument("--library", type=Path, default=ROOT / "library")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    try:
        cards = load_jsonl(args.library / "index.jsonl")
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"[Error] Cannot read library: {exc}", file=sys.stderr)
        return 2
    if args.show:
        selected = next((card for card in cards if card.get("id") == args.show), None)
        if not selected:
            print(f"[Error] Unknown card: {args.show}", file=sys.stderr)
            return 2
        path = ROOT / selected["path"]
        try:
            markdown = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"[Error] Cannot read card: {exc}", file=sys.stderr)
            return 2
        print(hide_solution_sections(markdown) if args.blind else markdown, end="")
        return 0
    if not args.query:
        parser.error("query is required unless --show is used")
    matches = search(cards, args.query, args.mode, args.result_type, args.limit, args.blind)
    print(json.dumps({"query": args.query, "count": len(matches), "results": matches}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
