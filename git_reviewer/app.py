"""Application module for git-reviewer."""

from __future__ import annotations

from . import __version__

PROJECT_NAME = "git-reviewer"
PROJECT_DESCRIPTION = "AI-powered code review tool using multiple LLM models"


def get_application_info() -> dict[str, str]:
    """Return basic metadata about the application."""

    return {
        "name": PROJECT_NAME,
        "description": PROJECT_DESCRIPTION,
        "version": __version__,
    }
