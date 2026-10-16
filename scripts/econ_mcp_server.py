#!/usr/bin/env python3
"""Local stdio MCP interface to the existing research validators and iteration loop."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from mcp.server import MCPServer


SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent


def invoke(script: str, root: Path, *arguments: str, timeout: int = 900) -> dict:
    try:
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / script), *arguments],
            cwd=root, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "failed", "error": f"{script} timed out after {timeout} seconds"}
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"status": "failed", "error": completed.stderr.strip() or completed.stdout.strip(), "exit_code": completed.returncode}
    if not isinstance(result, dict):
        return {"status": "failed", "error": f"{script} returned non-object JSON"}
    result["exit_code"] = completed.returncode
    return result


def create_server(project_root: Path) -> MCPServer:
    root = project_root.resolve()
    if not root.is_dir():
        raise ValueError(f"project root does not exist: {root}")
    mcp = MCPServer("invisible-hands-for-economists")

    @mcp.tool()
    def project_status() -> dict:
        """Read the frozen research contract, latest ledger state, and artifact presence."""
        contract_path = root / "research/contract.json"
        ledger_path = root / "research/ledger.jsonl"
        rework_path = root / "research/rework-state.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8")) if contract_path.is_file() else None
        events = []
        malformed_events = 0
        if ledger_path.is_file():
            for line in ledger_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    malformed_events += 1
                    continue
                if isinstance(event, dict):
                    events.append(event)
                else:
                    malformed_events += 1
        return {
            "root": str(root), "contract": contract, "event_count": len(events),
            "malformed_event_count": malformed_events,
            "latest_event": events[-1] if events else None,
            "rework_state": json.loads(rework_path.read_text(encoding="utf-8")) if rework_path.is_file() else None,
            "package_declared": (root / "research/package.json").is_file(),
            "candidate_actions_declared": (root / "research/dream-actions.json").is_file(),
        }

    @mcp.tool()
    def audit_package() -> dict:
        """Run the declared package gates and return each pass or failure reason."""
        return invoke("check_research_package.py", root, "--root", str(root), "--config", str(root / "research/package.json"))

    @mcp.tool()
    def run_workflow() -> dict:
        """Run the frozen contract workflow, replay, build, and delivery gates."""
        contract = root / "research/contract-input.json"
        if not contract.is_file():
            return {"status": "blocked", "error": "research/contract-input.json is missing"}
        return invoke("run_research_workflow.py", root, "--root", str(root), "--contract", str(contract), "--json")

    @mcp.tool()
    def run_iteration(max_steps: int = 1, max_cost: float = 10.0) -> dict:
        """Run bounded declared research actions, recording gate feedback and cost."""
        if max_steps < 1 or max_steps > 20 or max_cost <= 0:
            return {"status": "blocked", "error": "max_steps must be 1..20 and max_cost must be positive"}
        actions = root / "research/dream-actions.json"
        if not actions.is_file():
            return {"status": "blocked", "error": "research/dream-actions.json is missing"}
        return invoke(
            "dream_replay_simulator.py", root, "--online", "--root", str(root),
            "--tree", str(root / "research/discovery_tree.jsonl"),
            "--actions", str(actions), "--adapter", str(SCRIPTS / "research_action_adapter.py"),
            "--config", str(root / "research/package.json"),
            "--max-steps", str(max_steps), "--max-cost", str(max_cost),
            timeout=3600,
        )

    @mcp.resource("econ://workflow", mime_type="text/markdown")
    def workflow_guide() -> str:
        """The research agent's one-shot workflow and honest completion rules."""
        return (REPO / "references/workflow_execution.md").read_text(encoding="utf-8")

    @mcp.prompt()
    def research_question(question: str) -> str:
        """Start bounded research from a question using this server's workflow."""
        return (
            f"Research question: {question}\n\n"
            "Read econ://workflow. Freeze the original question and delivery scope, then investigate, "
            "write artifacts, audit, and iterate within the declared budget. Call run_workflow at the "
            "start and after material changes. Follow next_tasks and rework_plan after a failed gate. "
            "Report complete only when every applicable gate passes; "
            "otherwise report blocked evidence and preserved artifacts."
        )
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="project directory available to this MCP server")
    args = parser.parse_args()
    create_server(args.root).run()


if __name__ == "__main__":
    main()
