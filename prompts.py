"""MCP prompt definitions and registration for SmartStudyMCP."""

from __future__ import annotations

from typing import Callable

from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> dict[str, Callable[..., str]]:
    """Register reusable study prompts on the shared FastMCP server."""

    @mcp.prompt()
    def weekly_study_plan(
        subjects: str,
        available_hours: str,
        upcoming_deadlines: str = "None supplied",
    ) -> str:
        """Ask the AI client for a realistic weekly study schedule."""
        return (
            f"Create a realistic one-week study schedule for these subjects: {subjects}. "
            f"Available study time: {available_hours}. "
            f"Upcoming deadlines: {upcoming_deadlines}. "
            "Include breaks, review sessions, and a manageable daily workload. "
            "State assumptions."
        )

    @mcp.prompt()
    def explain_topic(topic: str) -> str:
        """Ask the AI client to explain a topic clearly with examples."""
        return (
            f"Explain {topic} clearly for a student. Start with the core idea, define key "
            "terms, give at least one concrete example, and finish with a short "
            "understanding check."
        )

    @mcp.prompt()
    def quiz_me(subject_or_notes: str) -> str:
        """Ask the AI client to quiz the student interactively."""
        return (
            f"Quiz me on this subject or these notes: {subject_or_notes}. "
            "Ask one question at a time, wait for my answer, then give constructive "
            "feedback. Do not present uncertain claims as verified facts."
        )

    @mcp.prompt()
    def summarize_notes(notes: str) -> str:
        """Ask the AI client to summarize notes into key points."""
        return (
            f"Summarize these study notes into concise key points: {notes}. "
            "Preserve important caveats, define unfamiliar terms, and do not add "
            "unsupported facts."
        )

    return {
        "weekly_study_plan": weekly_study_plan,
        "explain_topic": explain_topic,
        "quiz_me": quiz_me,
        "summarize_notes": summarize_notes,
    }
