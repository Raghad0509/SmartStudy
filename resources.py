"""MCP resource definitions and registration for SmartStudyMCP."""

from __future__ import annotations

import json
from typing import Callable

from mcp.server.fastmcp import FastMCP

from database import StudyDatabase


def register_resources(
    mcp: FastMCP, database_provider: Callable[[], StudyDatabase]
) -> dict[str, Callable[[], str]]:
    """Register SQLite-backed resources on the shared FastMCP server."""

    @mcp.resource("study://tasks")
    def study_tasks_resource() -> str:
        """Read all persisted tasks as JSON."""
        return json.dumps(
            database_provider().list_tasks(), indent=2, ensure_ascii=False
        )

    @mcp.resource("study://notes")
    def study_notes_resource() -> str:
        """Read all persisted notes as JSON."""
        return json.dumps(
            database_provider().list_notes(), indent=2, ensure_ascii=False
        )

    @mcp.resource("study://summary")
    def study_summary_resource() -> str:
        """Read dashboard counts for persisted tasks."""
        return json.dumps(database_provider().get_summary(), indent=2)

    return {
        "study_tasks_resource": study_tasks_resource,
        "study_notes_resource": study_notes_resource,
        "study_summary_resource": study_summary_resource,
    }
