"""Tests for MCP tool behavior and registered MCP primitives."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import server
from database import StudyDatabase


class ToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        server.database = StudyDatabase(Path(self.temp_dir.name) / "tools.sqlite3")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_task_tools_and_clear_delete_confirmation(self) -> None:
        added = server.add_study_task("Essay", "English", "2030-03-01", "medium")
        task_id = added["task"]["id"]
        self.assertTrue(added["success"])
        self.assertEqual(server.update_study_task(task_id, status="completed")["task"]["status"], "completed")
        self.assertEqual(server.list_study_tasks(status="completed")["count"], 1)
        deleted = server.delete_study_task(task_id)
        self.assertTrue(deleted["deleted"])
        self.assertIn("deleted", deleted["message"])
        self.assertFalse(server.delete_study_task(task_id)["success"])

    def test_note_tools_and_empty_search(self) -> None:
        saved = server.save_study_note("Gravity", "Physics", "Masses attract each other.")
        self.assertTrue(saved["success"])
        self.assertEqual(server.search_study_notes(keyword="attract")["count"], 1)
        self.assertEqual(server.search_study_notes(subject="Chemistry")["count"], 0)
        self.assertIn("error", server.search_study_notes())

    def test_invalid_tool_inputs_and_quiz_label(self) -> None:
        self.assertFalse(server.add_study_task("", "Math", "2030-01-01", "high")["success"])
        self.assertIn("error", server.update_study_task(1))
        self.assertIn("error", server.generate_quiz(text=" ", number_of_questions=1))
        quiz = server.generate_quiz(text="Water boils at 100 C.", number_of_questions=2)
        self.assertFalse(quiz["verified"])
        self.assertEqual(len(quiz["questions"]), 2)
        self.assertIn("not verified", quiz["label"])

    def test_study_plan_and_live_resources(self) -> None:
        server.add_study_task("Review", "Math", "2030-01-01", "high")
        self.assertIn("Review", server.study_tasks_resource())
        self.assertIn('"total": 1', server.study_summary_resource())
        plan = server.create_study_plan(
            ["Math", "Biology"],
            90,
            [{"subject": "Math", "due_date": "2030-01-01"}],
        )
        self.assertEqual(len(plan["schedule"]), 7)
        self.assertEqual(
            sum(session["minutes"] for session in plan["schedule"][0]["sessions"]),
            90,
        )

    def test_tools_resources_and_prompts_are_registered(self) -> None:
        tools = {tool.name for tool in server.mcp._tool_manager.list_tools()}
        resources = {
            str(resource.uri) for resource in server.mcp._resource_manager.list_resources()
        }
        prompts = {prompt.name for prompt in server.mcp._prompt_manager.list_prompts()}
        self.assertTrue(
            {
                "add_study_task",
                "list_study_tasks",
                "update_study_task",
                "delete_study_task",
                "save_study_note",
                "search_study_notes",
                "generate_quiz",
                "create_study_plan",
            }.issubset(tools)
        )
        self.assertEqual(
            resources, {"study://tasks", "study://notes", "study://summary"}
        )
        self.assertEqual(
            prompts,
            {"weekly_study_plan", "explain_topic", "quiz_me", "summarize_notes"},
        )


if __name__ == "__main__":
    unittest.main()
