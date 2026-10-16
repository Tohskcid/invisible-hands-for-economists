import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from mcp import Client
except ImportError:
    Client = None


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(Client is None, "install the mcp optional dependency to run MCP protocol tests")
class MCPServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_tools_resource_and_prompt_over_in_memory_mcp(self):
        spec = importlib.util.spec_from_file_location("econ_mcp_server", ROOT / "scripts/econ_mcp_server.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            server = module.create_server(Path(directory))
            async with Client(server, raise_exceptions=True) as client:
                listed = await client.list_tools()
                names = {tool.name for tool in listed.tools}
                self.assertEqual(names, {"project_status", "audit_package", "run_workflow", "run_iteration"})

                status = await client.call_tool("project_status", {})
                status_data = json.loads(status.content[0].text)
                self.assertEqual(status_data["event_count"], 0)
                self.assertEqual(status_data["malformed_event_count"], 0)
                self.assertIsNone(status_data["rework_state"])
                self.assertFalse(status_data["package_declared"])

                missing = await client.call_tool("run_workflow", {})
                self.assertEqual(json.loads(missing.content[0].text)["status"], "blocked")

                guide = await client.read_resource("econ://workflow")
                self.assertIn("One-shot research execution", guide.contents[0].text)

                prompt = await client.get_prompt("research_question", {"question": "Does X affect Y?"})
                self.assertIn("Does X affect Y?", prompt.messages[0].content.text)

    async def test_status_survives_partial_ledger_line(self):
        spec = importlib.util.spec_from_file_location("econ_mcp_server", ROOT / "scripts/econ_mcp_server.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "research").mkdir()
            (project / "research/ledger.jsonl").write_text('{"event_type":"start"}\n{"event_type":', encoding="utf-8")
            async with Client(module.create_server(project), raise_exceptions=True) as client:
                status = await client.call_tool("project_status", {})
                data = json.loads(status.content[0].text)
                self.assertEqual(data["event_count"], 1)
                self.assertEqual(data["malformed_event_count"], 1)

    async def test_workflow_tool_runs_real_feasibility_gate(self):
        spec = importlib.util.spec_from_file_location("econ_mcp_server", ROOT / "scripts/econ_mcp_server.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            research = project / "research"
            research.mkdir()
            (research / "manifest.jsonl").write_text("\n".join(json.dumps(item) for item in [
                {"id": "source", "type": "evidence", "source": "synthetic fixture", "locator": "fixture:1", "verified_at": "2026-10-16"},
                {"id": "claim", "type": "claim", "statement": "Scoped proposition", "role": "conclusion", "central": True,
                 "status": "provisional", "scope": "theoretical", "uncertainty": "awaits proof", "evidence_ids": ["source"]},
            ]) + "\n", encoding="utf-8")
            (research / "package.json").write_text(json.dumps({
                "mode": "theory", "deliverable": "feasibility_report", "claim_scope": "research-only",
                "mechanism_scope": "not-claimed", "manifest": "research/manifest.jsonl",
            }), encoding="utf-8")
            (research / "contract-input.json").write_text(json.dumps({
                "mode": "theory", "deliverable": "feasibility_report", "claim_scope": "research-only",
                "question": "Can a scoped proposition be investigated?", "max_budget": 10,
            }), encoding="utf-8")
            async with Client(module.create_server(project), raise_exceptions=True) as client:
                result = await client.call_tool("run_workflow", {})
                report = json.loads(result.content[0].text)
                self.assertEqual(report["status"], "complete")
                self.assertTrue(report["package_audit"]["valid"])

    async def test_iteration_repairs_a_real_failed_gate(self):
        spec = importlib.util.spec_from_file_location("econ_mcp_server", ROOT / "scripts/econ_mcp_server.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            research = project / "research"
            scripts = project / "scripts"
            research.mkdir()
            scripts.mkdir()
            manifest = research / "manifest.jsonl"
            manifest.write_text("invalid json\n", encoding="utf-8")
            valid_records = [
                {"id": "source", "type": "evidence", "source": "synthetic fixture", "locator": "fixture:1", "verified_at": "2026-10-16"},
                {"id": "claim", "type": "claim", "statement": "Scoped proposition", "role": "conclusion", "central": True,
                 "status": "provisional", "scope": "theoretical", "uncertainty": "awaits proof", "evidence_ids": ["source"]},
            ]
            (scripts / "fix_manifest.py").write_text(
                "from pathlib import Path\n"
                f"Path('research/manifest.jsonl').write_text({repr(chr(10).join(json.dumps(item) for item in valid_records) + chr(10))})\n",
                encoding="utf-8",
            )
            (research / "package.json").write_text(json.dumps({
                "mode": "theory", "deliverable": "feasibility_report", "claim_scope": "research-only",
                "mechanism_scope": "not-claimed", "manifest": "research/manifest.jsonl",
            }), encoding="utf-8")
            (research / "dream-actions.json").write_text(json.dumps({"actions": [{
                "id": "fix-json", "stage": "gate_remediation", "kind": "schema-repair",
                "estimated_cost": 1, "payload": {"command": [sys.executable, "scripts/fix_manifest.py"]},
            }]}), encoding="utf-8")
            async with Client(module.create_server(project), raise_exceptions=True) as client:
                result = await client.call_tool("run_iteration", {"max_steps": 2, "max_cost": 2})
                report = json.loads(result.content[0].text)
                self.assertEqual(report["status"], "complete")
                self.assertTrue(report["package"]["valid"])
                self.assertTrue((research / "discovery_tree.jsonl").is_file())
