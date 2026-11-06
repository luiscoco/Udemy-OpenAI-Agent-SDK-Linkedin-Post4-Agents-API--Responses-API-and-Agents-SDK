"""Optional integration test: real SDK tool and SQLite, fake Runner model execution."""
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core import ROOT, load_state
from runtimes import sdk_turn
from test_app import test_directory


@unittest.skipUnless(importlib.util.find_spec("agents"), "Install requirements.txt for SDK integration test")
class SDKIntegrationTests(unittest.TestCase):
    def test_real_local_tool_and_sqlite_survive_two_invocations(self):
        from agents.tool_context import ToolContext
        observed_history = []

        async def fake_run(agent, question, *, session, max_turns):
            self.assertEqual(max_turns, 6)
            history = await session.get_items()
            observed_history.append(len(history))
            context = ToolContext(context=None, tool_name="get_sales_facts",
                                  tool_call_id="test-call", tool_arguments="{}")
            output = await agent.tools[0].on_invoke_tool(context, "{}")
            self.assertIn('"gross_margin_percent": "44.00"', output)
            await session.add_items([
                {"role": "user", "content": question},
                {"role": "assistant", "content": "Margin is 44%."},
            ])
            return SimpleNamespace(final_output="Margin is 44%.")

        with test_directory() as directory:
            state_file = Path(directory) / "student.json"
            state = {"turns": []}
            with patch("agents.Runner.run", new=fake_run):
                for question in ["Summarize", "Explain that margin"]:
                    output, events = asyncio.run(sdk_turn("test-model", question, state,
                                                         ROOT / "data" / "sales.json", state_file))
                    self.assertEqual(output, "Margin is 44%.")
                    self.assertIn("local function tool: get_sales_facts", events)
                    state = load_state(state_file)
            self.assertEqual(observed_history, [0, 2])


if __name__ == "__main__":
    unittest.main()
