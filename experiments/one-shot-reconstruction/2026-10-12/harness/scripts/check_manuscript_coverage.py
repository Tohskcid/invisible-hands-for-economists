#!/usr/bin/env python3
"""Validate that manuscript sections are backed by claims and hashed artifacts."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


HASH = re.compile(r"^[0-9a-f]{64}$")
MODES = {"empirical", "theory", "structural"}
STATUSES = {"ready", "blocked", "not_applicable"}
KINDS = {
    "section_packet", "literature", "data_documentation", "analysis_code",
    "result", "table", "figure", "diagnostic", "design_audit", "proof",
    "model", "appendix", "reproduction",
}
REQUIRED_ROLES = {
    "empirical": {"introduction", "literature", "data", "identification", "results", "robustness", "conclusion", "appendix"},
    "theory": {"introduction", "literature", "model", "results", "conclusion", "appendix"},
    "structural": {"introduction", "literature", "data", "identification", "model", "results", "counterfactual", "robustness", "conclusion", "appendix"},
}
ARTIFACT_REQUIREMENTS = {
    "data": ({"data_documentation"}, {"analysis_code"}),
    "identification": ({"diagnostic", "design_audit"}, {"analysis_code"}),
    "results": ({"result"}, {"analysis_code"}, {"table", "figure"}),
    "robustness": ({"result"}, {"analysis_code"}, {"table", "figure", "diagnostic"}),
    "mechanism": ({"result"}, {"analysis_code"}, {"table", "figure", "diagnostic"}),
    "heterogeneity": ({"result"}, {"analysis_code"}, {"table", "figure"}),
    "external_validity": ({"result"}, {"analysis_code"}, {"table", "figure", "diagnostic"}),
    "model": ({"model", "proof"},),
    "counterfactual": ({"model"}, {"result"}, {"analysis_code"}),
    "appendix": ({"appendix"},),
}


def artifact_requirements(mode: str, role: str) -> tuple[set[str], ...]:
    if mode == "theory":
        return {
            "model": ({"model"},),
            "results": ({"proof"},),
            "appendix": ({"appendix"},),
        }.get(role, ())
    if mode == "structural" and role == "model":
        return ({"model"}, {"analysis_code"})
    return ARTIFACT_REQUIREMENTS.get(role, ())


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def manuscript_headings(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.casefold() == ".tex":
        return {value.strip() for value in re.findall(r"\\section\*?\{([^{}]+)\}", text)}
    headings = [match.group(1).strip() for match in re.finditer(r"^#{1,2}\s+(.+?)\s*$", text, re.MULTILINE)]
    return set(headings[1:] if headings and text.lstrip().startswith("# ") else headings)


def claim_ids(path: Path) -> set[str]:
    result: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        value = json.loads(raw)
        if isinstance(value, dict) and value.get("type") == "claim" and nonempty(value.get("id")):
            result.add(value["id"])
    return result


def artifact_file(root: Path, value: object, label: str, errors: list[str]) -> Path | None:
    if not nonempty(value):
        errors.append(f"{label} requires path")
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{label} must stay below the project root")
        return None
    target = root.joinpath(*path.parts).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label} resolves outside the project root")
        return None
    if not target.is_file():
        errors.append(f"{label} does not exist: {value}")
        return None
    return target


def validate(document: object, root: Path, manuscript: Path, manifest: Path) -> dict:
    errors: list[str] = []
    if not isinstance(document, dict):
        return {"valid": False, "ready": False, "sections": 0, "errors": ["coverage must be a JSON object"]}
    if document.get("schema_version") != "1":
        errors.append("schema_version must be '1'")
    mode = document.get("mode")
    if not isinstance(mode, str) or mode not in MODES:
        errors.append(f"mode must be one of {sorted(MODES)}")
        mode = ""
    manuscript_digest = hashlib.sha256(manuscript.read_bytes()).hexdigest()
    if document.get("manuscript_sha256") != manuscript_digest:
        errors.append("manuscript_sha256 is missing or stale")
    try:
        known_claims = claim_ids(manifest)
        headings = manuscript_headings(manuscript)
    except (OSError, json.JSONDecodeError) as exc:
        return {"valid": False, "ready": False, "sections": 0, "errors": [f"cannot read manuscript or manifest: {exc}"]}

    sections = document.get("sections")
    if not isinstance(sections, list) or not sections:
        return {"valid": False, "ready": False, "sections": 0, "errors": errors + ["sections must be a non-empty list"]}
    seen_ids: set[str] = set()
    covered_headings: set[str] = set()
    roles: dict[str, list[str]] = {}
    all_ready = True
    for index, section in enumerate(sections, 1):
        if not isinstance(section, dict):
            errors.append(f"section {index} must be an object")
            all_ready = False
            continue
        section_id = section.get("id")
        if not nonempty(section_id):
            errors.append(f"section {index} requires id")
            section_id = str(index)
        elif section_id in seen_ids:
            errors.append(f"duplicate section id {section_id!r}")
        seen_ids.add(section_id)
        prefix = f"section {section_id!r}"
        role = section.get("role")
        if not nonempty(role):
            errors.append(f"{prefix} requires role")
            role = ""
        roles.setdefault(role, []).append(section_id)
        status = section.get("status")
        if not isinstance(status, str) or status not in STATUSES:
            errors.append(f"{prefix} status must be one of {sorted(STATUSES)}")
            all_ready = False
        elif status != "ready":
            all_ready = False
            if not nonempty(section.get("gap")):
                errors.append(f"{prefix} {status} status requires gap or justification")

        section_headings = section.get("headings")
        if not isinstance(section_headings, list) or not section_headings or not all(nonempty(item) for item in section_headings):
            errors.append(f"{prefix} requires non-empty headings")
        else:
            for heading in section_headings:
                if heading in covered_headings:
                    errors.append(f"manuscript heading {heading!r} is assigned more than once")
                covered_headings.add(heading)
                if heading not in headings:
                    errors.append(f"{prefix} references absent manuscript heading {heading!r}")

        claims = section.get("claim_ids")
        if status == "ready" and (not isinstance(claims, list) or not claims):
            errors.append(f"{prefix} ready section requires claim_ids")
        elif isinstance(claims, list):
            for claim_id in claims:
                if not isinstance(claim_id, str) or claim_id not in known_claims:
                    errors.append(f"{prefix} references unknown claim {claim_id!r}")

        artifacts = section.get("artifacts", [])
        kinds: set[str] = set()
        if not isinstance(artifacts, list):
            errors.append(f"{prefix} artifacts must be a list")
            artifacts = []
        for artifact_index, artifact in enumerate(artifacts, 1):
            label = f"{prefix} artifact {artifact_index}"
            if not isinstance(artifact, dict):
                errors.append(f"{label} must be an object")
                continue
            kind = artifact.get("kind")
            if not isinstance(kind, str) or kind not in KINDS:
                errors.append(f"{label} kind must be one of {sorted(KINDS)}")
            else:
                kinds.add(kind)
            target = artifact_file(root, artifact.get("path"), label, errors)
            digest = artifact.get("sha256")
            if not isinstance(digest, str) or not HASH.fullmatch(digest):
                errors.append(f"{label} requires lowercase SHA-256")
            elif target is not None and hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                errors.append(f"{label} checksum mismatch")
        if status == "ready":
            if "section_packet" not in kinds:
                errors.append(f"{prefix} ready section requires a section_packet artifact")
            for alternatives in artifact_requirements(mode, role):
                if not kinds.intersection(alternatives):
                    errors.append(f"{prefix} role {role!r} requires one of {sorted(alternatives)}")

    missing_headings = sorted(headings - covered_headings)
    extra_headings = sorted(covered_headings - headings)
    if missing_headings:
        errors.append(f"manuscript headings missing from coverage: {missing_headings}")
    if extra_headings:
        errors.append(f"coverage headings absent from manuscript: {extra_headings}")
    missing_roles = sorted(REQUIRED_ROLES.get(mode, set()) - set(roles))
    if missing_roles:
        errors.append(f"required {mode} roles missing: {missing_roles}")
    required_not_ready = sorted(role for role in REQUIRED_ROLES.get(mode, set()) if role in roles and not any(
        section.get("role") == role and section.get("status") == "ready" for section in sections if isinstance(section, dict)
    ))
    if required_not_ready:
        all_ready = False
    return {
        "valid": not errors,
        "ready": not errors and all_ready and not required_not_ready,
        "sections": len(sections),
        "required_roles_not_ready": required_not_ready,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage", type=Path)
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    paths = [args.coverage, args.manuscript, args.manifest]
    paths = [path if path.is_absolute() else root / path for path in paths]
    if not all(path.is_file() for path in paths):
        print("[Error] Coverage, manuscript, and manifest files must exist", file=sys.stderr)
        return 2
    try:
        document = json.loads(paths[0].read_text(encoding="utf-8"))
        report = validate(document, root, paths[1], paths[2])
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[Error] Cannot check manuscript coverage: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("valid" if report["valid"] else "invalid")
        for error in report["errors"]:
            print(f"- {error}")
    return 0 if report["valid"] and (report["ready"] or not args.require_ready) else 1


if __name__ == "__main__":
    raise SystemExit(main())
