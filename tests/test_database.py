"""Tests for SQLite persistence and validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from database import StudyDatabase


class StudyDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = StudyDatabase(Path(self.temp_dir.name) / "study.sqlite3")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_task_persistence_update_and_delete(self) -> None:
        created = self.db.add_task("Read chapter", "Biology", "2030-01-02", "HIGH")
        reopened = StudyDatabase(self.db.path)
        self.assertEqual(reopened.list_tasks()[0]["id"], created["id"])
        updated = reopened.update_task(created["id"], status="completed")
        self.assertEqual(updated["status"], "completed")
        self.assertTrue(reopened.delete_task(created["id"]))
        self.assertFalse(reopened.delete_task(created["id"]))

    def test_note_search_by_keyword_and_subject(self) -> None:
        self.db.save_note("Cell structure", "Biology", "Mitochondria produce energy.")
        self.db.save_note("Fractions", "Math", "A fraction represents part of a whole.")
        self.assertEqual(len(self.db.search_notes(keyword="MITOCHONDRIA")), 1)
        self.assertEqual(len(self.db.search_notes(subject="math")), 1)
        self.assertEqual(self.db.search_notes(keyword="absent"), [])

    def test_invalid_inputs_and_empty_search(self) -> None:
        with self.assertRaises(ValueError):
            self.db.add_task("", "Biology", "2030-01-02", "high")
        with self.assertRaises(ValueError):
            self.db.add_task("Read", "Biology", "02-01-2030", "high")
        with self.assertRaises(ValueError):
            self.db.add_task("Read", "Biology", "2030-01-02", "urgent")
        with self.assertRaises(ValueError):
            self.db.update_task(0, status="completed")
        with self.assertRaises(ValueError):
            self.db.search_notes()
        self.assertEqual(self.db.list_tasks(status="completed"), [])

    def test_empty_summary_and_overdue_counts(self) -> None:
        self.assertEqual(
            self.db.get_summary(),
            {"total": 0, "completed": 0, "pending": 0, "overdue": 0},
        )
        self.db.add_task("Past task", "History", "2000-01-01", "low")
        self.db.add_task("Finished", "History", "2000-01-01", "medium")
        tasks = self.db.list_tasks()
        self.db.update_task(tasks[1]["id"], status="completed")
        self.assertEqual(
            self.db.get_summary(),
            {"total": 2, "completed": 1, "pending": 1, "overdue": 1},
        )


if __name__ == "__main__":
    unittest.main()
