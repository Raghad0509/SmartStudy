"""MCP tool definitions and registration for SmartStudyMCP."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from database import StudyDatabase


def register_tools(
    mcp: FastMCP, database_provider: Callable[[], StudyDatabase]
) -> dict[str, Callable[..., Any]]:
    """Register study tools on the shared FastMCP server."""

    @mcp.tool()
    def add_study_task(
        title: str, subject: str, due_date: str, priority: str
    ) -> dict[str, Any]:
        """Create a study task using a YYYY-MM-DD due date and low/medium/high priority."""
        try:
            task = database_provider().add_task(title, subject, due_date, priority)
            return {"success": True, "task": task}
        except (ValueError, OSError) as exc:
            return {"success": False, "error": str(exc)}

    @mcp.tool()
    def list_study_tasks(
        status: str | None = None, subject: str | None = None
    ) -> dict[str, Any]:
        """List tasks, optionally filtered by pending/in_progress/completed status or subject."""
        try:
            tasks = database_provider().list_tasks(status=status, subject=subject)
            return {"tasks": tasks, "count": len(tasks)}
        except (ValueError, OSError) as exc:
            return {"error": str(exc), "tasks": []}

    @mcp.tool()
    def update_study_task(
        task_id: int,
        title: str | None = None,
        subject: str | None = None,
        due_date: str | None = None,
        priority: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Update one or more task fields."""
        updates = {
            key: value
            for key, value in {
                "title": title,
                "subject": subject,
                "due_date": due_date,
                "priority": priority,
                "status": status,
            }.items()
            if value is not None
        }
        try:
            task = database_provider().update_task(task_id, **updates)
            if task is None:
                return {
                    "success": False,
                    "error": f"No study task found with ID {task_id}.",
                }
            return {"success": True, "task": task}
        except (ValueError, OSError) as exc:
            return {"success": False, "error": str(exc)}

    @mcp.tool()
    def delete_study_task(task_id: int) -> dict[str, Any]:
        """Delete a task by ID and confirm whether it was deleted."""
        try:
            deleted = database_provider().delete_task(task_id)
            if not deleted:
                return {
                    "success": False,
                    "deleted": False,
                    "message": f"No task found with ID {task_id}.",
                }
            return {
                "success": True,
                "deleted": True,
                "message": f"Study task {task_id} was deleted.",
            }
        except (ValueError, OSError) as exc:
            return {"success": False, "deleted": False, "error": str(exc)}

    @mcp.tool()
    def save_study_note(
        title: str, subject: str, content: str
    ) -> dict[str, Any]:
        """Save a study note with a title, subject, and non-empty content."""
        try:
            note = database_provider().save_note(title, subject, content)
            return {"success": True, "note": note}
        except (ValueError, OSError) as exc:
            return {"success": False, "error": str(exc)}

    @mcp.tool()
    def search_study_notes(
        keyword: str | None = None, subject: str | None = None
    ) -> dict[str, Any]:
        """Search saved notes by keyword in title/content, by subject, or both."""
        try:
            notes = database_provider().search_notes(
                keyword=keyword, subject=subject
            )
            return {"notes": notes, "count": len(notes)}
        except (ValueError, OSError) as exc:
            return {"error": str(exc), "notes": []}

    @mcp.tool()
    def generate_quiz(
        text: str | None = None,
        note_ids: list[int] | None = None,
        subject: str | None = None,
        number_of_questions: int = 5,
    ) -> dict[str, Any]:
        """Create practice prompts from text or saved notes, not verified facts."""
        if (
            isinstance(number_of_questions, bool)
            or not isinstance(number_of_questions, int)
            or not 1 <= number_of_questions <= 20
        ):
            return {"error": "number_of_questions must be an integer from 1 to 20."}
        source_parts: list[str] = []
        try:
            if text is not None:
                if not text.strip():
                    return {"error": "text must not be empty when supplied."}
                source_parts.append(text.strip())
            elif note_ids:
                notes_by_id = {
                    note["id"]: note for note in database_provider().list_notes()
                }
                for note_id in note_ids:
                    if (
                        isinstance(note_id, bool)
                        or not isinstance(note_id, int)
                        or note_id < 1
                    ):
                        return {"error": "note_ids must contain positive integer IDs."}
                    note = notes_by_id.get(note_id)
                    if note is None:
                        return {"error": f"No saved note found with ID {note_id}."}
                    source_parts.extend([note["title"], note["content"]])
            elif subject is not None:
                notes = database_provider().search_notes(subject=subject)
                source_parts.extend(note["content"] for note in notes)
                if not notes:
                    return {"error": f"No saved notes found for subject '{subject}'."}
            else:
                return {
                    "error": "Provide text, note_ids, or a subject with saved notes."
                }
        except (ValueError, OSError) as exc:
            return {"error": str(exc)}

        source = " ".join(source_parts)
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", source)
            if sentence.strip()
        ]
        if not sentences:
            return {"error": "The supplied source contains no usable text."}
        questions = []
        for index in range(number_of_questions):
            sentence = sentences[index % len(sentences)]
            questions.append(
                {
                    "number": index + 1,
                    "question": f"Explain this idea in your own words: {sentence}",
                    "source_excerpt": sentence,
                }
            )
        return {
            "label": "Generated practice questions — not verified facts.",
            "verified": False,
            "questions": questions,
            "count": len(questions),
        }

    @mcp.tool()
    def create_study_plan(
        subjects: list[str],
        available_minutes_per_day: int,
        deadlines: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Create a seven-day schedule from subjects, daily time, and deadlines."""
        if not subjects or any(
            not isinstance(subject, str) or not subject.strip()
            for subject in subjects
        ):
            return {"error": "subjects must contain at least one non-empty subject."}
        if (
            isinstance(available_minutes_per_day, bool)
            or not isinstance(available_minutes_per_day, int)
            or available_minutes_per_day < 1
        ):
            return {
                "error": "available_minutes_per_day must be a positive integer."
            }
        subjects = list(dict.fromkeys(subject.strip() for subject in subjects))
        due_by_subject: dict[str, date] = {}
        for deadline in deadlines or []:
            if not isinstance(deadline, dict) or not isinstance(
                deadline.get("subject"), str
            ):
                return {"error": "Each deadline must contain a subject and due_date."}
            deadline_subject = deadline["subject"].strip()
            try:
                due_date = deadline.get("due_date", "")
                deadline_date = date.fromisoformat(due_date)
            except (TypeError, ValueError):
                return {
                    "error": "Each deadline due_date must use YYYY-MM-DD format."
                }
            if deadline_date.isoformat() != due_date:
                return {
                    "error": "Each deadline due_date must use YYYY-MM-DD format."
                }
            if not deadline_subject:
                return {"error": "Deadline subject must not be empty."}
            due_by_subject[deadline_subject.casefold()] = deadline_date

        today = date.today()
        schedule = []
        for offset in range(7):
            session_date = today + timedelta(days=offset)
            ranked_subjects = sorted(
                subjects,
                key=lambda item: (
                    due_by_subject.get(item.casefold(), date.max),
                    (subjects.index(item) - offset) % len(subjects),
                ),
            )
            minutes_each = available_minutes_per_day // len(ranked_subjects)
            remainder = available_minutes_per_day % len(ranked_subjects)
            sessions = [
                {
                    "subject": item,
                    "minutes": minutes_each + (1 if index < remainder else 0),
                    "deadline": (
                        due_by_subject[item.casefold()].isoformat()
                        if item.casefold() in due_by_subject
                        else None
                    ),
                }
                for index, item in enumerate(ranked_subjects)
            ]
            schedule.append({"date": session_date.isoformat(), "sessions": sessions})
        return {
            "duration_days": 7,
            "available_minutes_per_day": available_minutes_per_day,
            "schedule": schedule,
            "guidance": "Adjust sessions to your energy and actual progress.",
        }

    return {
        "add_study_task": add_study_task,
        "list_study_tasks": list_study_tasks,
        "update_study_task": update_study_task,
        "delete_study_task": delete_study_task,
        "save_study_note": save_study_note,
        "search_study_notes": search_study_notes,
        "generate_quiz": generate_quiz,
        "create_study_plan": create_study_plan,
    }
