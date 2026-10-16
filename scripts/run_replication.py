#!/usr/bin/env python3
"""Execute clean replication, verify numerical reproducibility, and detect stale artifacts."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_command(command: list[str], cwd: Path, env: dict | None = None, timeout: int = 300) -> dict:
    started_at = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "duration_seconds": round(time.time() - started_at, 3),
            "passed": completed.returncode == 0,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
    except subprocess.TimeoutExpired:
        return {
            "command": command,
            "exit_code": -1,
            "duration_seconds": round(time.time() - started_at, 3),
            "passed": False,
            "stdout": "",
            "stderr": f"command timed out after {timeout} seconds",
        }


def flatten_dict(d: dict, prefix: str = "") -> dict[str, float | int]:
    items: dict[str, float | int] = {}
    for k, v in d.items():
        new_key = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key))
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            items[new_key] = v
    return items


def verify_numeric_agreement(
    actual: dict[str, float | int],
    expected: dict[str, float | int],
    tolerance: float = 1e-4,
) -> list[str]:
    errors = []
    for key, exp_val in expected.items():
        if key not in actual:
            errors.append(f"missing result key {key!r} in regenerated results")
            continue
        act_val = actual[key]
        diff = abs(act_val - exp_val)
        if diff > tolerance:
            errors.append(
                f"numeric discrepancy for {key!r}: generated {act_val} but expected {exp_val} (diff {diff:g} > {tolerance:g})"
            )
    return errors


def run_replication(
    root: Path,
    entry_commands: list[list[str]],
    raw_inputs: list[str],
    generated_targets: list[str] | None = None,
    expected_results_file: Path | None = None,
    tolerance: float = 1e-4,
    clean_before_run: bool = True,
    timeout: int = 300,
    generated: list[str] | None = None,
) -> dict:
    if generated_targets is None:
        generated_targets = generated or []
    root = root.resolve()
    errors: list[str] = []
    missing_inputs: list[str] = []

    def below_root(value: str | Path, label: str) -> tuple[str, Path] | None:
        path = Path(value)
        try:
            if ".." in path.parts or path == Path("."):
                raise ValueError
            target = (path if path.is_absolute() else root / path).resolve()
            relative = target.relative_to(root)
            if not relative.parts:
                raise ValueError
        except ValueError:
            errors.append(f"unsafe {label} path: {value}")
            return None
        return relative.as_posix(), target

    raw_paths = [below_root(raw, "raw input") for raw in raw_inputs]
    generated_paths = [below_root(gen, "generated output") for gen in generated_targets]
    expected_path = below_root(expected_results_file, "expected results") if expected_results_file else None
    if any(value is None for value in raw_paths + generated_paths) or (expected_results_file and expected_path is None):
        return {"reproducible": False, "clean_replay_verified": False, "missing_raw_inputs": [],
                "stale_artifacts": [], "numeric_discrepancies": [], "errors": errors, "commands": []}

    raw_paths = [value for value in raw_paths if value is not None]
    generated_paths = [value for value in generated_paths if value is not None]
    raw_set = {name for name, _ in raw_paths}
    if any(name in raw_set or any(raw.startswith(name + "/") for raw in raw_set) for name, _ in generated_paths):
        errors.append("generated outputs must not contain raw inputs")
    if len({name for name, _ in generated_paths}) != len(generated_paths):
        errors.append("generated output paths must be unique")

    # 1. Verify raw inputs exist and are non-empty
    for raw, target in raw_paths:
        if not target.is_file() or target.stat().st_size == 0:
            missing_inputs.append(raw)
    if missing_inputs:
        errors.append(f"missing or empty raw input files: {missing_inputs}")

    if errors:
        return {"reproducible": False, "clean_replay_verified": False, "missing_raw_inputs": missing_inputs,
                "stale_artifacts": [], "numeric_discrepancies": [], "errors": errors, "commands": []}

    # Load canonical expected results if provided
    expected_numbers: dict[str, float | int] = {}
    if expected_path and not expected_path[1].is_file():
        errors.append(f"expected results file missing: {expected_path[0]}")
    if expected_path and expected_path[1].is_file():
        try:
            exp_data = json.loads(expected_path[1].read_text(encoding="utf-8"))
            if not isinstance(exp_data, dict):
                raise ValueError("expected results must be a JSON object")
            numeric_source = exp_data.get("results", exp_data)
            if not isinstance(numeric_source, dict):
                raise ValueError("results must be a JSON object")
            expected_numbers = flatten_dict(numeric_source)
            source_hashes = exp_data.get("source_sha256", {})
            if not isinstance(source_hashes, dict):
                raise ValueError("source_sha256 must be a JSON object")
            for raw, target in raw_paths:
                declared_hash = source_hashes.get(raw)
                if declared_hash and declared_hash != sha256_file(target):
                    errors.append(f"source hash mismatch for raw input: {raw}")
        except (json.JSONDecodeError, OSError, ValueError, TypeError) as exc:
            errors.append(f"cannot read expected results file: {exc}")

    # Replay in a temporary copy so a validation run cannot erase the author's results.
    with tempfile.TemporaryDirectory(prefix="research-replay-") as directory:
        replay_root = Path(directory) / "project"
        shutil.copytree(root, replay_root, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache"))
        deleted_outputs = []
        stale_check_timestamps: dict[str, float] = {}
        for gen, _ in generated_paths:
            target = replay_root / gen
            if clean_before_run and target.exists():
                deleted_outputs.append(gen)
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            elif target.exists():
                stale_check_timestamps[gen] = target.stat().st_mtime

        execution_start_time = time.time()
        command_reports = []
        env = os.environ.copy()
        for cmd in entry_commands:
            rep = run_command(cmd, cwd=replay_root, env=env, timeout=timeout)
            command_reports.append(rep)
            if not rep["passed"]:
                errors.append(f"command {cmd} failed with exit code {rep['exit_code']}")
                break

        stale_artifacts = []
        missing_outputs = []
        output_hashes: dict[str, str] = {}
        artifact_discrepancies = []
        for gen, _ in generated_paths:
            target = replay_root / gen
            if not target.exists():
                missing_outputs.append(gen)
            else:
                if gen in stale_check_timestamps and target.stat().st_mtime <= stale_check_timestamps[gen]:
                    stale_artifacts.append(gen)
                if target.is_file():
                    output_hashes[gen] = sha256_file(target)
                    original = root / gen
                    if original.is_file() and sha256_file(original) != output_hashes[gen]:
                        artifact_discrepancies.append(f"generated artifact differs from recorded output: {gen}")

        if missing_outputs:
            errors.append(f"replay failed to generate expected outputs: {missing_outputs}")
        if stale_artifacts:
            errors.append(f"stale artifacts detected (not regenerated during replay): {stale_artifacts}")
        errors.extend(artifact_discrepancies)

        numeric_discrepancies = []
        if expected_path:
            regenerated_results = replay_root / expected_path[0]
            if regenerated_results.is_file():
                try:
                    actual_data = json.loads(regenerated_results.read_text(encoding="utf-8"))
                    if not isinstance(actual_data, dict):
                        raise ValueError("regenerated results must be a JSON object")
                    actual_source = actual_data.get("results", actual_data)
                    if not isinstance(actual_source, dict):
                        raise ValueError("regenerated results field must be a JSON object")
                    actual_numbers = flatten_dict(actual_source)
                    numeric_discrepancies = verify_numeric_agreement(actual_numbers, expected_numbers, tolerance)
                    errors.extend(numeric_discrepancies)
                except (json.JSONDecodeError, OSError, ValueError, TypeError) as exc:
                    errors.append(f"cannot read regenerated results file: {exc}")
            else:
                errors.append(f"regenerated results file missing: {expected_path[0]}")

    passed = (not errors) and all(rep["passed"] for rep in command_reports)

    return {
        "reproducible": passed,
        "clean_replay_verified": passed and clean_before_run,
        "execution_duration_seconds": round(time.time() - execution_start_time, 3),
        "commands": command_reports,
        "deleted_outputs_before_run": deleted_outputs,
        "missing_raw_inputs": missing_inputs,
        "stale_artifacts": stale_artifacts,
        "numeric_discrepancies": numeric_discrepancies,
        "artifact_discrepancies": artifact_discrepancies,
        "generated_sha256": output_hashes,
        "replay_isolated_copy": True,
        "errors": sorted(set(errors)),
        "disclaimer": (
            "Computational replication verified: does not imply causal identification, "
            "historical fidelity, or novel contribution."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, help="Replication config JSON file")
    parser.add_argument("--command", nargs="+", action="append", help="Entry command to execute")
    parser.add_argument("--raw-inputs", nargs="*", default=[], help="Raw input files to verify")
    parser.add_argument("--generated", nargs="*", default=[], help="Generated output files or directories")
    parser.add_argument("--results", type=Path, help="Results JSON file to check against pre-existing values")
    parser.add_argument("--tolerance", type=float, default=1e-4)
    parser.add_argument("--clean", action="store_true", help="Delete generated outputs before executing")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()

    commands = args.command or []
    raw_inputs = list(args.raw_inputs)
    generated = list(args.generated)
    results_file = args.results
    tolerance = args.tolerance
    clean = args.clean

    if args.config:
        config_path = args.config if args.config.is_absolute() else root / args.config
        if not config_path.is_file():
            print(f"[Error] Replication config not found: {config_path}", file=sys.stderr)
            return 2
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            if "commands" in cfg and not commands:
                commands = cfg["commands"]
            if "raw_inputs" in cfg and not raw_inputs:
                raw_inputs = cfg["raw_inputs"]
            if "generated" in cfg and not generated:
                generated = cfg["generated"]
            if "results" in cfg and results_file is None:
                results_file = root / cfg["results"]
            if "tolerance" in cfg:
                tolerance = float(cfg["tolerance"])
            if "clean" in cfg and not clean:
                clean = bool(cfg["clean"])
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[Error] Cannot parse replication config: {exc}", file=sys.stderr)
            return 2

    if not commands:
        print("[Error] No replication entry commands specified", file=sys.stderr)
        return 2

    report = run_replication(
        root=root,
        entry_commands=commands,
        raw_inputs=raw_inputs,
        generated_targets=generated,
        expected_results_file=results_file,
        tolerance=tolerance,
        clean_before_run=clean,
        timeout=args.timeout,
    )

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    return 0 if report["reproducible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
