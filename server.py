"""SmartStudyMCP application entry point and shared MCP server."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from database import StudyDatabase
from prompts import register_prompts
from resources import register_resources
from tools import register_tools


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
LOGGER = logging.getLogger("smartstudymcp")
DEFAULT_DB_PATH = Path(__file__).with_name("smartstudy.db")
database = StudyDatabase(os.environ.get("SMARTSTUDY_DB_PATH", str(DEFAULT_DB_PATH)))

mcp = FastMCP(
    "SmartStudyMCP",
    instructions=(
        "A local study organizer. Generated quizzes are practice material, "
        "not verified facts."
    ),
)

tool_handlers = register_tools(mcp, lambda: database)
resource_handlers = register_resources(mcp, lambda: database)
prompt_handlers = register_prompts(mcp)

add_study_task = tool_handlers["add_study_task"]
list_study_tasks = tool_handlers["list_study_tasks"]
update_study_task = tool_handlers["update_study_task"]
delete_study_task = tool_handlers["delete_study_task"]
save_study_note = tool_handlers["save_study_note"]
search_study_notes = tool_handlers["search_study_notes"]
generate_quiz = tool_handlers["generate_quiz"]
create_study_plan = tool_handlers["create_study_plan"]
study_tasks_resource = resource_handlers["study_tasks_resource"]
study_notes_resource = resource_handlers["study_notes_resource"]
study_summary_resource = resource_handlers["study_summary_resource"]


def main() -> None:
    """Run the MCP server over stdio; stdout is reserved for MCP messages."""
    LOGGER.info("Starting SmartStudyMCP with SQLite database at %s", database.path)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
