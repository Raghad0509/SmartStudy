"""SQLite persistence for SmartStudyMCP."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Generator


VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES = {"pending", "in_progress", "completed"}


class StudyDatabase:
    """Provide validated CRUD operations over a local SQLite database."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the database tables when they do not already exist."""
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS study_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    priority TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high')),
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'in_progress', 'completed')),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS study_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _required_text(value: str, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} is required and must be non-empty text.")
        return value.strip()

    @staticmethod
    def _validate_date(value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("due_date must be a date in YYYY-MM-DD format.")
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("due_date must be a valid date in YYYY-MM-DD format.") from exc
        if parsed.isoformat() != value:
            raise ValueError("due_date must use YYYY-MM-DD format.")
        return value

    @staticmethod
    def _validate_id(task_id: int) -> int:
        if isinstance(task_id, bool) or not isinstance(task_id, int) or task_id < 1:
            raise ValueError("Task ID must be a positive integer.")
        return task_id

    @staticmethod
    def _record(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row is not None else None

    def add_task(
        self, title: str, subject: str, due_date: str, priority: str
    ) -> dict[str, Any]:
        """Insert a task and return its saved representation."""
        title = self._required_text(title, "title")
        subject = self._required_text(subject, "subject")
        due_date = self._validate_date(due_date)
        if not isinstance(priority, str) or priority.lower() not in VALID_PRIORITIES:
            raise ValueError("priority must be one of: low, medium, high.")
        priority = priority.lower()
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO study_tasks (title, subject, due_date, priority, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, subject, due_date, priority, created_at),
            )
            row = connection.execute(
                "SELECT * FROM study_tasks WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        if row is None:
            raise RuntimeError("The task was inserted but could not be retrieved.")
        return dict(row)

    def list_tasks(
        self, status: str | None = None, subject: str | None = None
    ) -> list[dict[str, Any]]:
        """Return tasks, optionally filtered by status and/or subject."""
        clauses: list[str] = []
        values: list[str] = []
        if status is not None:
            if not isinstance(status, str) or status.lower() not in VALID_STATUSES:
                raise ValueError(
                    "status must be one of: pending, in_progress, completed."
                )
            clauses.append("status = ?")
            values.append(status.lower())
        if subject is not None:
            subject = self._required_text(subject, "subject")
            clauses.append("subject = ? COLLATE NOCASE")
            values.append(subject)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM study_tasks{where} ORDER BY due_date, id", values
            ).fetchall()
        return [dict(row) for row in rows]

    def update_task(self, task_id: int, **updates: str) -> dict[str, Any] | None:
        """Update supplied task fields; reject empty or unsupported updates."""
        task_id = self._validate_id(task_id)
        allowed = {"title", "subject", "due_date", "priority", "status"}
        if not updates or set(updates) - allowed:
            raise ValueError(
                "Provide at least one valid field: title, subject, due_date, priority, status."
            )
        values: dict[str, str] = {}
        for field, value in updates.items():
            if field in {"title", "subject"}:
                values[field] = self._required_text(value, field)
            elif field == "due_date":
                values[field] = self._validate_date(value)
            elif field == "priority":
                if not isinstance(value, str) or value.lower() not in VALID_PRIORITIES:
                    raise ValueError("priority must be one of: low, medium, high.")
                values[field] = value.lower()
            elif field == "status":
                if not isinstance(value, str) or value.lower() not in VALID_STATUSES:
                    raise ValueError(
                        "status must be one of: pending, in_progress, completed."
                    )
                values[field] = value.lower()
        assignments = ", ".join(f"{field} = ?" for field in values)
        with self._connection() as connection:
            cursor = connection.execute(
                f"UPDATE study_tasks SET {assignments} WHERE id = ?",
                (*values.values(), task_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT * FROM study_tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return self._record(row)

    def delete_task(self, task_id: int) -> bool:
        """Delete a task and report whether it existed."""
        task_id = self._validate_id(task_id)
        with self._connection() as connection:
            cursor = connection.execute("DELETE FROM study_tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0

    def save_note(self, title: str, subject: str, content: str) -> dict[str, Any]:
        """Save a note without replacing any existing note."""
        title = self._required_text(title, "title")
        subject = self._required_text(subject, "subject")
        content = self._required_text(content, "content")
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO study_notes (title, subject, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (title, subject, content, created_at),
            )
            row = connection.execute(
                "SELECT * FROM study_notes WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        if row is None:
            raise RuntimeError("The note was inserted but could not be retrieved.")
        return dict(row)

    def search_notes(
        self, keyword: str | None = None, subject: str | None = None
    ) -> list[dict[str, Any]]:
        """Search note titles and content, optionally by subject."""
        if keyword is None and subject is None:
            raise ValueError("Provide a keyword, a subject, or both to search notes.")
        clauses: list[str] = []
        values: list[str] = []
        if keyword is not None:
            keyword = self._required_text(keyword, "keyword")
            clauses.append("(title LIKE ? COLLATE NOCASE OR content LIKE ? COLLATE NOCASE)")
            pattern = f"%{keyword}%"
            values.extend((pattern, pattern))
        if subject is not None:
            subject = self._required_text(subject, "subject")
            clauses.append("subject = ? COLLATE NOCASE")
            values.append(subject)
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM study_notes WHERE {' AND '.join(clauses)} "
                "ORDER BY created_at DESC, id DESC",
                values,
            ).fetchall()
        return [dict(row) for row in rows]

    def list_notes(self) -> list[dict[str, Any]]:
        """Return all saved notes in creation order."""
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM study_notes ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_summary(self) -> dict[str, int]:
        """Return total, completed, pending, and overdue task counts."""
        today = date.today().isoformat()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                    SUM(CASE WHEN status != 'completed' THEN 1 ELSE 0 END) AS pending,
                    SUM(CASE WHEN status != 'completed' AND due_date < ? THEN 1 ELSE 0 END)
                        AS overdue
                FROM study_tasks
                """,
                (today,),
            ).fetchone()
        return {
            "total": row["total"] or 0,
            "completed": row["completed"] or 0,
            "pending": row["pending"] or 0,
            "overdue": row["overdue"] or 0,
        }
