#!/usr/bin/env python3
"""Validate a JSONL research provenance graph."""

import argparse
import json
import sys
from pathlib import Path


LINKS = {
    "experiment": ("hypothesis_id", "hypothesis"),
    "run": ("experiment_id", "experiment"),
}
LIST_LINKS = {
    "finding": ("run_ids", "run"),
    "claim": ("evidence_ids", "evidence"),
}
REQUIRED = {
    "hypothesis": ("statement", "falsifier"),
    "experiment": ("hypothesis_id", "validation"),
    "run": ("experiment_id", "harness_version", "status", "artifact"),
    "evidence": ("source", "locator", "verified_at"),
    "finding": ("statement", "run_ids", "status"),
    "claim": ("statement",),
    "dataset": ("name", "source", "locator", "verified_at", "access_status", "license"),
    "proxy": ("name", "reason", "generator", "seed", "schema", "intended_use"),
}


def load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    records, errors = [], []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid JSON ({exc.msg})")
            continue
        if not isinstance(value, dict):
            errors.append(f"line {line_no}: record must be an object")
            continue
        value["_line"] = line_no
        records.append(value)
    return records, errors


def validate(records: list[dict]) -> list[str]:
    errors: list[str] = []
    by_id: dict[str, dict] = {}
    for record in records:
        line = record["_line"]
        record_id = record.get("id")
        kind = record.get("type")
        if not isinstance(record_id, str) or not record_id.strip():
            errors.append(f"line {line}: missing non-empty id")
        elif record_id in by_id:
            errors.append(f"line {line}: duplicate id {record_id!r}")
        else:
            by_id[record_id] = record
        if kind not in REQUIRED:
            errors.append(f"line {line}: unknown type {kind!r}")
            continue
        for field in REQUIRED[kind]:
            if record.get(field) in (None, "", []):
                errors.append(f"line {line}: {kind} requires {field}")

    for record in records:
        kind, line = record.get("type"), record["_line"]
        if kind in LINKS:
            field, target_type = LINKS[kind]
            target = by_id.get(record.get(field))
            if target is None or target.get("type") != target_type:
                errors.append(f"line {line}: {field} must reference a {target_type}")
        if kind in LIST_LINKS:
            field, target_type = LIST_LINKS[kind]
            values = record.get(field, [])
            if isinstance(values, list):
                for value in values:
                    target = by_id.get(value)
                    if target is None or target.get("type") != target_type:
                        errors.append(f"line {line}: {field} entry {value!r} must reference a {target_type}")
            elif values not in (None, ""):
                errors.append(f"line {line}: {field} must be a list")
        if kind == "claim":
            finding_ids = record.get("finding_ids", [])
            evidence_ids = record.get("evidence_ids", [])
            premise_ids = record.get("premise_ids", [])
            if not isinstance(finding_ids, list):
                errors.append(f"line {line}: finding_ids must be a list")
            if not isinstance(evidence_ids, list):
                errors.append(f"line {line}: evidence_ids must be a list")
            if not isinstance(premise_ids, list):
                errors.append(f"line {line}: premise_ids must be a list")
            if not evidence_ids and not finding_ids and not premise_ids:
                errors.append(f"line {line}: claim requires evidence_ids, finding_ids, or premise_ids")
            for value in finding_ids if isinstance(finding_ids, list) else []:
                target = by_id.get(value)
                if target is None or target.get("type") != "finding":
                    errors.append(f"line {line}: finding_ids entry {value!r} must reference a finding")
            for value in premise_ids if isinstance(premise_ids, list) else []:
                target = by_id.get(value)
                if value == record.get("id"):
                    errors.append(f"line {line}: claim cannot cite itself as a premise")
                elif target is None or target.get("type") != "claim":
                    errors.append(f"line {line}: premise_ids entry {value!r} must reference a claim")
        if kind in {"run", "claim"}:
            data_ids = record.get("data_ids", [])
            if not isinstance(data_ids, list):
                errors.append(f"line {line}: data_ids must be a list")
            else:
                for value in data_ids:
                    target = by_id.get(value)
                    if target is None or target.get("type") not in {"dataset", "proxy"}:
                        errors.append(f"line {line}: data_ids entry {value!r} must reference a dataset or proxy")

    claims = {record["id"]: record for record in records if record.get("type") == "claim" and isinstance(record.get("id"), str)}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit_claim(claim_id: str) -> None:
        if claim_id in visiting:
            errors.append(f"line {claims[claim_id]['_line']}: claim premise cycle reaches {claim_id!r}")
            return
        if claim_id in visited:
            return
        visiting.add(claim_id)
        premise_ids = claims[claim_id].get("premise_ids", [])
        for premise_id in premise_ids if isinstance(premise_ids, list) else []:
            if premise_id in claims:
                visit_claim(premise_id)
        visiting.remove(claim_id)
        visited.add(claim_id)

    for claim_id in claims:
        visit_claim(claim_id)

    proxy_memo: dict[str, bool] = {}

    def claim_uses_proxy(claim_id: str, stack: set[str]) -> bool:
        if claim_id in proxy_memo:
            return proxy_memo[claim_id]
        if claim_id in stack:
            return False
        record = claims[claim_id]
        data_ids = set(record.get("data_ids", [])) if isinstance(record.get("data_ids", []), list) else set()
        for finding_id in record.get("finding_ids", []) if isinstance(record.get("finding_ids", []), list) else []:
            finding = by_id.get(finding_id, {})
            for run_id in finding.get("run_ids", []) if isinstance(finding.get("run_ids", []), list) else []:
                run = by_id.get(run_id, {})
                if isinstance(run.get("data_ids", []), list):
                    data_ids.update(run["data_ids"])
        tainted = any(by_id.get(value, {}).get("type") == "proxy" for value in data_ids)
        for premise_id in record.get("premise_ids", []) if isinstance(record.get("premise_ids", []), list) else []:
            if premise_id in claims:
                tainted = tainted or claim_uses_proxy(premise_id, stack | {claim_id})
        proxy_memo[claim_id] = tainted
        return tainted

    for record in records:
        if record.get("type") != "claim":
            continue
        claim_id = record.get("id")
        if isinstance(claim_id, str) and claim_id in claims and claim_uses_proxy(claim_id, set()) and record.get("scope") != "proxy_only":
            errors.append(f"line {record['_line']}: claim using proxy data requires scope 'proxy_only'")
    return errors


def validate_argument(records: list[dict]) -> list[str]:
    errors: list[str] = []
    claims = {record["id"]: record for record in records if record.get("type") == "claim" and isinstance(record.get("id"), str)}
    central = [record for record in claims.values() if record.get("central") is True]
    conclusions = [record for record in central if record.get("role") == "conclusion"]
    if not conclusions:
        errors.append("argument graph requires at least one central conclusion")
    for record in central:
        line = record["_line"]
        if record.get("role") not in {"premise", "intermediate", "conclusion"}:
            errors.append(f"line {line}: central claim requires role premise, intermediate, or conclusion")
        if record.get("status") not in {"supported", "provisional", "contradicted", "unsupported"}:
            errors.append(f"line {line}: central claim requires a valid status")
        for field in ("scope", "uncertainty"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                errors.append(f"line {line}: central claim requires non-empty {field}")

    grounded_memo: dict[str, bool] = {}

    def grounded(claim_id: str, stack: set[str]) -> bool:
        if claim_id in grounded_memo:
            return grounded_memo[claim_id]
        if claim_id in stack:
            return False
        record = claims[claim_id]
        result = bool(record.get("evidence_ids") or record.get("finding_ids"))
        for premise_id in record.get("premise_ids", []) if isinstance(record.get("premise_ids", []), list) else []:
            if premise_id in claims:
                result = result or grounded(premise_id, stack | {claim_id})
        grounded_memo[claim_id] = result
        return result

    def ancestors(claim_id: str) -> set[str]:
        premises = claims[claim_id].get("premise_ids", [])
        result, stack = set(), list(premises) if isinstance(premises, list) else []
        while stack:
            current = stack.pop()
            if current in result or current not in claims:
                continue
            result.add(current)
            more = claims[current].get("premise_ids", [])
            if isinstance(more, list):
                stack.extend(more)
        return result

    for record in conclusions:
        line, claim_id = record["_line"], record["id"]
        if not grounded(claim_id, set()):
            errors.append(f"line {line}: central conclusion has no path to evidence or finding")
        if record.get("status") == "supported":
            weak = [value for value in ancestors(claim_id) if claims[value].get("status") in {"contradicted", "unsupported"}]
            if weak:
                errors.append(f"line {line}: supported conclusion depends on contradicted or unsupported premises {sorted(weak)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--json", action="store_true", help="emit a machine-readable report")
    parser.add_argument("--require-argument-graph", action="store_true")
    args = parser.parse_args()
    if not args.manifest.is_file():
        print(f"[Error] File not found: {args.manifest}", file=sys.stderr)
        return 2
    records, errors = load_jsonl(args.manifest)
    errors.extend(validate(records))
    if args.require_argument_graph:
        errors.extend(validate_argument(records))
    report = {"valid": not errors, "records": len(records), "errors": errors}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("valid" if not errors else "invalid")
        for error in errors:
            print(f"- {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
