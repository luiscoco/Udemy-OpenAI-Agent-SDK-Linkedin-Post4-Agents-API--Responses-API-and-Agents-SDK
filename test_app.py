"""Offline tests and API contract tests with fake clients: never make network calls."""
import json
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace as Obj
from uuid import uuid4
import unittest

from core import ROOT, load_state, sales_facts, save_json, state_path
from runtimes import consume_managed, direct_response, offline


@contextmanager
def test_directory():
    # Inherit workspace permissions; restrictive tempfile ACLs can break sandboxed Windows runs.
    path = ROOT / "storage" / ("test_" + uuid4().hex)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        for child in path.iterdir():
            child.unlink()
        path.rmdir()


class LessonTests(unittest.TestCase):
    def test_margin_uses_revenue_not_cost(self):
        facts = sales_facts()
        self.assertEqual(facts["revenue"], "20000.00")
        self.assertEqual(facts["gross_profit"], "8800.00")
        self.assertEqual(facts["gross_margin_percent"], "44.00")

    def test_zero_revenue_and_invalid_amounts(self):
        with test_directory() as directory:
            path = Path(directory) / "data.json"
            data = {"company": "Demo", "period": "Test", "currency": "EUR",
                    "products": [{"revenue": "0", "cost": "10"}]}
            save_json(path, data)
            self.assertIsNone(sales_facts(path)["gross_margin_percent"])
            for bad in ["NaN", "Infinity", "-1", "not a number"]:
                data["products"][0]["revenue"] = bad
                save_json(path, data)
                with self.assertRaises(ValueError):
                    sales_facts(path)

    def test_session_paths_are_isolated_and_reject_traversal(self):
        root = Path("storage")
        self.assertNotEqual(state_path(root, "offline", "sdk", "a"), state_path(root, "live", "sdk", "a"))
        self.assertNotEqual(state_path(root, "live", "sdk", "a"), state_path(root, "live", "managed", "a"))
        for bad in ["../escape", "a/b", "", "a" * 65]:
            with self.assertRaises(ValueError):
                state_path(root, "offline", "sdk", bad)

    def test_offline_state_survives_reload_without_remote_identifiers(self):
        with test_directory() as directory:
            path = Path(directory) / "state.json"
            state = load_state(path)
            answer, _ = offline("managed", "Summarize", state, ROOT / "data" / "sales.json")
            state["turns"].append({"answer": answer})
            save_json(path, state)
            restored = load_state(path)
            next_answer, _ = offline("managed", "Follow up", restored, ROOT / "data" / "sales.json")
            self.assertIn("turn 2", next_answer)
            self.assertNotIn("managed_session_id", restored)
            self.assertTrue(restored["simulated_handle"].startswith("demo_"))

    def test_responses_continuation_and_instructions_sent_each_turn(self):
        calls = []
        def create(**params):
            calls.append(params)
            return Obj(id=f"resp_{len(calls)}", status="completed", output_text="Margin is 44%.")
        client = Obj(responses=Obj(create=create))
        state = {"turns": []}
        direct_response(client, "test-model", "Summarize", state, sales_facts())
        direct_response(client, "test-model", "Why?", state, sales_facts())
        self.assertNotIn("previous_response_id", calls[0])
        self.assertIn("Verified sales facts", calls[0]["input"])
        self.assertEqual(calls[1]["previous_response_id"], "resp_1")
        self.assertEqual(calls[1]["input"], "Why?")
        self.assertEqual(calls[0]["instructions"], calls[1]["instructions"])
        self.assertEqual(state["previous_response_id"], "resp_2")

    def test_failed_response_does_not_replace_saved_id(self):
        client = Obj(responses=Obj(create=lambda **_: Obj(id="bad", status="incomplete", output_text="")))
        state = {"previous_response_id": "old"}
        with self.assertRaises(RuntimeError):
            direct_response(client, "test", "Question", state, sales_facts())
        self.assertEqual(state["previous_response_id"], "old")

    def test_managed_requires_completed_root_turn(self):
        idle = Obj(type="agent.session.idle")
        child = Obj(type="agent.session.turn.completed", turn=Obj(subagent_id="child"))
        root = Obj(type="agent.session.turn.completed", turn=Obj(subagent_id=None))
        with self.assertRaises(RuntimeError):
            consume_managed([idle, child], [])
        consume_managed([idle, child, root], [])
        for kind in ["agent.session.turn.failed", "agent.session.turn.cancelled"]:
            with self.assertRaises(RuntimeError):
                consume_managed([Obj(type=kind, turn=Obj(subagent_id=None))], [])


if __name__ == "__main__":
    unittest.main()
