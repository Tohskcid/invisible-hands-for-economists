#!/usr/bin/env python3
"""Run applicable deterministic gates declared by a research package config."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath


PATH_FIELDS = {
    "topic_survey", "data_provenance", "manifest", "manuscript", "bibliography",
    "literature_archive", "coverage", "results", "design_audit", "structural_audit", "logic_review",
    "mechanism_audit", "mechanism_review", "real_world_audit", "text_audit", "latex_main", "latex_visual_review",
    "replication", "team_report", "substantive_review",
}
METADATA_FIELDS = {"claim_scope", "mechanism_scope"}
PROFILE_FIELDS = {"mode", "profile", "contract", "deliverable", "latex_build_dir", "latex_engine", "release_pdf", "unapplicable_justification"}
ALLOWED = PATH_FIELDS | METADATA_FIELDS | PROFILE_FIELDS

RESEARCH_PROFILES = {
    "empirical": {
        "manuscript": {"manifest", "topic_survey", "data_provenance", "results", "replication", "design_audit", "manuscript", "coverage", "bibliography", "literature_archive", "logic_review", "latex_main", "latex_visual_review", "latex_build_dir", "release_pdf"},
        "replication_package": {"data_provenance", "results", "replication"},
        "feasibility_report": {"topic_survey"},
    },
    "theory": {
        "manuscript": {"manifest", "manuscript", "coverage", "bibliography", "literature_archive", "logic_review", "latex_main", "latex_visual_review", "latex_build_dir", "release_pdf"},
        "feasibility_report": {"manifest"},
    },
    "structural": {
        "manuscript": {"manifest", "data_provenance", "results", "replication", "structural_audit", "manuscript", "coverage", "bibliography", "literature_archive", "logic_review", "latex_main", "latex_visual_review", "latex_build_dir", "release_pdf"},
        "feasibility_report": {"manifest", "structural_audit"},
    },
    "descriptive": {
        "manuscript": {"manifest", "topic_survey", "data_provenance", "results", "replication", "manuscript", "coverage", "bibliography", "literature_archive", "logic_review", "latex_main", "latex_visual_review", "latex_build_dir", "release_pdf"},
        "feasibility_report": {"topic_survey"},
    },
    "replication": {
        "manuscript": {"manifest", "data_provenance", "results", "replication", "manuscript", "coverage", "bibliography", "literature_archive", "logic_review", "latex_main", "latex_visual_review", "latex_build_dir", "release_pdf"},
        "replication_package": {"data_provenance", "results", "replication"},
    },
}

for profiles in RESEARCH_PROFILES.values():
    if "manuscript" in profiles:
        profiles["manuscript"].update({"topic_survey", "team_report", "substantive_review"})


def resolve(root: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} must stay below the package root")
    target = root.joinpath(*path.parts)
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{field} resolves outside the package root") from exc
    if not target.is_file():
        raise ValueError(f"{field} file does not exist: {value}")
    return target


def run(command: list[str]) -> dict:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "command": command,
        "passed": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def check(root: Path, config_path: Path, scripts: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("package config must be a JSON object")
    unknown = sorted(set(config) - ALLOWED)
    if unknown:
        raise ValueError(f"unknown package fields: {unknown}")
    mode = config.get("mode") or config.get("profile")
    deliverable = config.get("deliverable", "manuscript")
    if mode is not None:
        if mode not in RESEARCH_PROFILES:
            raise ValueError(f"unknown research mode/profile: {mode!r}; valid: {sorted(RESEARCH_PROFILES)}")
        if deliverable not in RESEARCH_PROFILES[mode]:
            raise ValueError(f"unknown deliverable {deliverable!r} for mode {mode!r}; valid: {sorted(RESEARCH_PROFILES[mode])}")
        required_fields = set(RESEARCH_PROFILES[mode][deliverable])
        justifications = config.get("unapplicable_justification", {})
        if not isinstance(justifications, dict):
            raise ValueError("unapplicable_justification must be an object")
        missing = sorted(required_fields - set(config))
        if missing:
            raise ValueError(
                f"research profile {mode}/{deliverable} requires {missing}; required gates cannot be waived by a package config"
            )
        if deliverable == "feasibility_report" and "latex_main" in config:
            raise ValueError("feasibility_report deliverable cannot claim manuscript delivery")

    paths = {field: resolve(root, config[field], field) for field in PATH_FIELDS if field in config}
    if "results" in paths and "data_provenance" not in paths:
        raise ValueError("results requires data_provenance; estimation is blocked without verified inputs")
    if "team_report" in paths and mode is None:
        raise ValueError("team_report requires a research mode")
    if "substantive_review" in paths and "manuscript" not in paths:
        raise ValueError("substantive_review requires manuscript")
    manuscript_requirements = {"manifest", "coverage", "bibliography", "literature_archive", "logic_review"}
    if "manuscript" in paths and not manuscript_requirements.issubset(paths):
        missing = sorted(manuscript_requirements - set(paths))
        raise ValueError(
            "manuscript requires manifest, coverage, bibliography, literature_archive, and logic_review; "
            f"missing {missing}"
        )
    if "coverage" in paths and not {"manuscript", "manifest"}.issubset(paths):
        raise ValueError("coverage requires manuscript and manifest")
    if ("bibliography" in paths) != ("literature_archive" in paths):
        raise ValueError("bibliography and literature_archive must be declared together")
    if "logic_review" in paths and not {"manuscript", "manifest"}.issubset(paths):
        raise ValueError("logic_review requires manuscript and manifest")
    if "latex_main" in paths and "latex_visual_review" not in paths:
        raise ValueError("latex_main requires latex_visual_review for delivery")
    if "latex_visual_review" in paths and "latex_main" not in paths:
        raise ValueError("latex_visual_review requires latex_main")
    claim_scope = config.get("claim_scope")
    if claim_scope is not None and claim_scope not in {"research-only", "real-world"}:
        raise ValueError("claim_scope must be 'research-only' or 'real-world'")
    if ("manuscript" in paths or "results" in paths) and claim_scope not in {"research-only", "real-world"}:
        raise ValueError("manuscript or results requires claim_scope 'research-only' or 'real-world'")
    if claim_scope == "real-world" and "real_world_audit" not in paths:
        raise ValueError("real-world claim_scope requires real_world_audit")
    mechanism_scope = config.get("mechanism_scope")
    if mechanism_scope is not None and mechanism_scope not in {"claimed", "not-claimed"}:
        raise ValueError("mechanism_scope must be 'claimed' or 'not-claimed'")
    if "manuscript" in paths and mechanism_scope not in {"claimed", "not-claimed"}:
        raise ValueError("manuscript requires mechanism_scope 'claimed' or 'not-claimed'")
    if mechanism_scope == "claimed" and not {"mechanism_audit", "mechanism_review"}.issubset(paths):
        raise ValueError("claimed mechanism_scope requires mechanism_audit and mechanism_review")
    if ("mechanism_audit" in paths) != ("mechanism_review" in paths):
        raise ValueError("mechanism_audit and mechanism_review must be declared together")

    checks: list[dict] = []
    python = sys.executable

    if "manuscript" in paths or "latex_main" in paths:
        checks.append(run([
            python, str(scripts / "check_project_layout.py"), "--root", str(root), "--json",
        ]))

    if "topic_survey" in paths:
        command = [
            python, str(scripts / "check_topic_survey.py"), str(paths["topic_survey"]),
            "--root", str(root), "--json",
        ]
        if deliverable != "feasibility_report":
            command.append("--require-approved")
        if "manuscript" in paths and "bibliography" in paths:
            command.extend(["--manuscript", str(paths["manuscript"]), "--bibliography", str(paths["bibliography"])])
        checks.append(run(command))
    if "data_provenance" in paths:
        command = [
            python, str(scripts / "check_data_provenance.py"), str(paths["data_provenance"]),
            "--root", str(root), "--json",
        ]
        if mode in {"empirical", "descriptive", "replication", "structural"}:
            command.append("--require-real")
        checks.append(run(command))
    if "literature_archive" in paths:
        checks.append(run([
            python, str(scripts / "check_literature_archive.py"), str(paths["literature_archive"]),
            "--bibliography", str(paths["bibliography"]), "--root", str(root),
            "--require-complete", "--json",
        ]))
    if "manifest" in paths:
        checks.append(run([python, str(scripts / "validate_research_manifest.py"), str(paths["manifest"]), "--require-argument-graph", "--json"]))
    if "coverage" in paths:
        checks.append(run([
            python, str(scripts / "check_manuscript_coverage.py"), str(paths["coverage"]),
            "--manuscript", str(paths["manuscript"]), "--manifest", str(paths["manifest"]),
            "--root", str(root), "--require-ready", "--json",
            "--require-limitations",
        ]))
    if "team_report" in paths:
        team_command = [
            python, str(scripts / "check_research_team.py"), str(paths["team_report"]),
            "--root", str(root), "--mode", str(mode), "--json",
        ]
        if "substantive_review" in paths:
            team_command.extend(["--review", str(paths["substantive_review"])])
        checks.append(run(team_command))
    if "substantive_review" in paths:
        command = [python, str(scripts / "check_substantive_review.py"), str(paths["substantive_review"]),
                   "--manuscript", str(paths["manuscript"]), "--root", str(root), "--json"]
        if "topic_survey" in paths:
            command.extend(["--topic-survey", str(paths["topic_survey"])])
        checks.append(run(command))
    if "manuscript" in paths and "manifest" in paths:
        checks.append(run([
            python, str(scripts / "audit_claims.py"), str(paths["manuscript"]), str(paths["manifest"]),
            "--strict-numbers", "--require-central-claims", "--json",
        ]))
    if "logic_review" in paths:
        checks.append(run([
            python, str(scripts / "check_logic_review.py"),
            "--manuscript", str(paths["manuscript"]), "--manifest", str(paths["manifest"]),
            "--review", str(paths["logic_review"]), "--require-pass", "--json",
        ]))
    if "results" in paths and "manuscript" not in paths and deliverable != "replication_package":
        raise ValueError("results requires manuscript")
    if "results" in paths and "manuscript" in paths:
        checks.append(run([
            python, str(scripts / "check_result_bindings.py"), "--results", str(paths["results"]),
            "--manuscript", str(paths["manuscript"]), "--root", str(root), "--json",
        ]))
    if "design_audit" in paths:
        checks.append(run([
            python, str(scripts / "check_design_audit.py"), str(paths["design_audit"]),
            "--root", str(root), "--require-pass", "--json",
        ]))
    if "mechanism_audit" in paths:
        checks.append(run([
            python, str(scripts / "check_mechanism_audit.py"), str(paths["mechanism_audit"]),
            "--root", str(root), "--review", str(paths["mechanism_review"]), "--require-pass", "--json",
        ]))
    if "structural_audit" in paths:
        checks.append(run([
            python, str(scripts / "check_structural_audit.py"), str(paths["structural_audit"]),
            "--root", str(root), "--require-pass", "--json",
        ]))
    if "real_world_audit" in paths:
        command = [
            python, str(scripts / "check_real_world_audit.py"), str(paths["real_world_audit"]),
            "--root", str(root), "--json",
        ]
        if claim_scope == "real-world":
            command.insert(-1, "--require-applicable")
        checks.append(run(command))
    if "text_audit" in paths:
        checks.append(run([
            python, str(scripts / "check_text_audit.py"), str(paths["text_audit"]),
            "--root", str(root), "--require-pass", "--json",
        ]))
    if "replication" in paths:
        checks.append(run([
            python, str(scripts / "run_replication.py"),
            "--root", str(root), "--config", str(paths["replication"]), "--clean", "--json",
        ]))
    if "latex_main" in paths:
        engine = config.get("latex_engine", "auto")
        build_dir_setting = config.get("latex_build_dir")
        build_path = None
        if build_dir_setting:
            build_setting_path = PurePosixPath(build_dir_setting)
            if build_setting_path.is_absolute() or ".." in build_setting_path.parts:
                raise ValueError("latex_build_dir must stay below the package root")
            build_path = root.joinpath(*build_setting_path.parts).resolve()
            try:
                build_path.relative_to(root.resolve())
            except ValueError as exc:
                raise ValueError("latex_build_dir resolves outside the package root") from exc

        release_pdf_args = []
        if "release_pdf" in config:
            rel_pdf = resolve(root, config["release_pdf"], "release_pdf")
            release_pdf_args = ["--release-pdf", str(rel_pdf)]

        # WP6: Single-build verification mode if report.json already exists in declared build dir
        if build_path and (build_path / "report.json").is_file():
            report_file = build_path / "report.json"
            build_report = json.loads(report_file.read_text(encoding="utf-8"))
            source_dir = Path(build_report.get("source_dir", "")).resolve()
            try:
                source_dir.relative_to(root.resolve())
                main_rel = paths["latex_main"].resolve().relative_to(source_dir).as_posix()
            except ValueError as exc:
                raise ValueError("existing build report does not bind declared latex_main") from exc
            recorded_hash = build_report.get("input_hashes", {}).get(main_rel)
            if recorded_hash != hashlib.sha256(paths["latex_main"].read_bytes()).hexdigest():
                raise ValueError("existing build report does not bind current latex_main bytes")
            finalize_cmd = [
                python, str(scripts / "check_latex.py"), "finalize",
                "--report", str(report_file),
                "--visual-review", str(paths["latex_visual_review"]),
                *release_pdf_args,
            ]
            checks.append(run(finalize_cmd))
        else:
            temp_context = None
            if build_path:
                build_dir = build_path
            else:
                temp_context = tempfile.TemporaryDirectory(prefix="research-latex-")
                build_dir = Path(temp_context.name) / "build"
            try:
                report_file = build_dir / "report.json"
                checks.append(run([
                    python, str(scripts / "check_latex.py"), "check",
                    "--main", str(paths["latex_main"]),
                    "--build-dir", str(build_dir),
                    "--report", str(report_file),
                    "--engine", str(engine),
                ]))
                checks.append(run([
                    python, str(scripts / "check_latex.py"), "finalize",
                    "--report", str(report_file),
                    "--visual-review", str(paths["latex_visual_review"]),
                    *release_pdf_args,
                ]))
            finally:
                if temp_context:
                    temp_context.cleanup()
    if not checks:
        raise ValueError("package config selects no checks")
    valid = all(item["passed"] for item in checks)
    returns = []
    for item in checks:
        if item["passed"]:
            continue
        try:
            target = json.loads(item.get("stdout", "")).get("return_to")
        except (AttributeError, json.JSONDecodeError):
            target = None
        if target and target not in returns:
            returns.append(target)
    return {
        "valid": valid,
        "iteration_required": not valid,
        "return_to": returns or (["gate_remediation"] if not valid else []),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("research/package.json"))
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    config = args.config if args.config.is_absolute() else root / args.config
    if not config.is_file():
        if args.allow_missing:
            # WP1 & Section 8.1 Scenario 1: missing/skipped config never counts as completed research
            print(json.dumps({
                "valid": False,
                "skipped": True,
                "error": f"package config {config} not found; missing/skipped config never counts as completed research"
            }, ensure_ascii=False, indent=2))
            return 2
        print(f"[Error] File not found: {config}", file=sys.stderr)
        return 2
    try:
        report = check(root, config, Path(__file__).resolve().parent)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[Error] Cannot check research package: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
