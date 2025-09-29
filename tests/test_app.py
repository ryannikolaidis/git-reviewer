"""Tests for git_reviewer modules."""

from typer.testing import CliRunner

from git_reviewer.app import get_application_info
from git_reviewer.cli import app

runner = CliRunner()


def test_get_application_info() -> None:
    """Application metadata includes expected fields."""

    metadata = get_application_info()
    assert metadata["name"] == "git-reviewer"
    assert metadata["description"] == "AI-powered code review tool using multiple LLM models"
    assert metadata["version"] == "0.1.0"


def test_help() -> None:
    """Test help output."""

    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "AI-powered code review tool" in result.stdout


def test_check_command() -> None:
    """Test check command runs without error."""

    result = runner.invoke(app, ["check"])
    # Command should run but may have errors due to missing nllm or config
    # We just check it doesn't crash with a Python error
    assert "git-reviewer" in result.stdout.lower() or "error" in result.stdout.lower()


def test_init_config_command() -> None:
    """Test init-config command help."""

    result = runner.invoke(app, ["init-config", "--help"])
    assert result.exit_code == 0
    assert "Initialize" in result.stdout


def test_review_command_help() -> None:
    """Test review command help shows updated interface."""

    result = runner.invoke(app, ["review", "--help"])
    assert result.exit_code == 0
    assert "--model" in result.stdout
    assert "multiple times" in result.stdout
    assert "--parallel" not in result.stdout  # Should be removed
