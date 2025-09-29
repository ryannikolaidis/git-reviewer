"""Tests for git-reviewer core functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from git_reviewer.config import DEFAULT_CONFIG, deep_merge_config, validate_config
from git_reviewer.context import build_repo_context, get_context_summary, is_binary_file
from git_reviewer.errors import ConfigurationError
from git_reviewer.nllm_runner import NLLMRunner
from git_reviewer.template import SafeTemplate, substitute_variables


class TestConfiguration:
    """Test configuration loading and validation."""

    def test_default_config_is_valid(self):
        """Test that the default configuration is valid."""
        validate_config(DEFAULT_CONFIG)

    def test_deep_merge_config(self):
        """Test deep merging of configuration dictionaries."""
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"b": 10}, "e": 4}

        result = deep_merge_config(base, override)

        assert result["a"]["b"] == 10  # overridden
        assert result["a"]["c"] == 2  # preserved
        assert result["d"] == 3  # preserved
        assert result["e"] == 4  # added

    def test_validate_config_missing_keys(self):
        """Test validation fails with missing required keys."""
        invalid_config = {"models": []}

        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(invalid_config)

        assert "Missing required configuration key" in str(exc_info.value)

    def test_validate_config_invalid_model(self):
        """Test validation fails with invalid model configuration."""
        invalid_config = {
            "models": [{"invalid": "model"}],  # missing 'name'
            "defaults": {},
            "git": {},
            "paths": {},
        }

        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(invalid_config)

        assert "missing required 'name' field" in str(exc_info.value)

    def test_validate_config_invalid_types(self):
        """Test validation fails with invalid types."""
        invalid_config = {
            "models": "not a list",  # should be list
            "defaults": {},
            "git": {},
            "paths": {},
        }

        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(invalid_config)

        assert "'models' must be a list" in str(exc_info.value)


class TestContext:
    """Test context file handling."""

    def test_build_repo_context_empty(self):
        """Test building context with no files."""
        result = build_repo_context([])
        assert result == ""

    def test_build_repo_context_single_file(self):
        """Test building context with a single file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            result = build_repo_context([temp_path])
            # Check for the filename (resolved path might differ)
            assert temp_path.name in result
            assert "test content" in result
        finally:
            temp_path.unlink()

    def test_build_repo_context_missing_file(self):
        """Test building context with missing file."""
        missing_path = Path("/nonexistent/file.txt")
        result = build_repo_context([missing_path])

        assert "[Error reading file:" in result
        assert str(missing_path) in result

    def test_is_binary_file(self):
        """Test binary file detection."""
        # Test with text file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is text content")
            text_path = Path(f.name)

        # Test with binary-like content
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as f:
            f.write(b"Binary content with \x00 null byte")
            binary_path = Path(f.name)

        try:
            assert not is_binary_file(text_path)
            assert is_binary_file(binary_path)
        finally:
            text_path.unlink()
            binary_path.unlink()

    def test_get_context_summary(self):
        """Test context summary generation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            summary = get_context_summary([temp_path])
            assert summary["total_files"] == 1
            assert summary["readable_files"] == 1
            assert summary["binary_files"] == 0
            assert summary["missing_files"] == 0
            assert summary["total_size_mb"] >= 0  # Small files might round to 0.0
        finally:
            temp_path.unlink()


class TestTemplate:
    """Test template processing."""

    def test_safe_template_basic(self):
        """Test basic template substitution."""
        template = SafeTemplate("Hello $name!")
        result = template.safe_substitute({"name": "World"})
        assert result == "Hello World!"

    def test_safe_template_missing_var(self):
        """Test template with missing variable."""
        template = SafeTemplate("Hello $name! Today is $day.")
        result = template.safe_substitute({"name": "World"})
        assert result == "Hello World! Today is $day."

    def test_substitute_variables(self):
        """Test variable substitution function."""
        content = "Repository: $repo_context\nDiff: $diff"
        variables = {"repo_context": "Context content", "diff": "Diff content"}

        result = substitute_variables(content, variables)
        assert "Context content" in result
        assert "Diff content" in result

    def test_substitute_variables_empty_content(self):
        """Test substitution with empty content."""
        result = substitute_variables("", {"var": "value"})
        assert result == ""


class TestNLLMRunner:
    """Test nllm integration."""

    def test_prepare_model_options_basic(self):
        """Test basic model options preparation."""
        config = {"defaults": {"timeout": 60, "retries": 2}}
        runner = NLLMRunner(config)

        model_config = {"name": "test-model", "options": ["-o", "temperature", "0.7"]}
        options = runner._prepare_model_options(model_config)

        assert options == ["test-model:-o:temperature:0.7"]

    def test_prepare_model_options_empty(self):
        """Test model options preparation with no options."""
        config = {"defaults": {}}
        runner = NLLMRunner(config)

        model_config = {"name": "test-model"}
        options = runner._prepare_model_options(model_config)

        assert options == []

    @patch("builtins.__import__")
    def test_check_nllm_available_success(self, mock_import):
        """Test successful nllm availability check."""
        mock_nllm = Mock()
        mock_nllm.__version__ = "0.1.0"
        mock_import.return_value = mock_nllm

        config = {"defaults": {}}
        runner = NLLMRunner(config)

        available, info = runner.check_nllm_available()

        assert available is True
        assert "0.1.0" in info

    @patch("builtins.__import__")
    def test_check_nllm_available_not_found(self, mock_import):
        """Test nllm not found."""
        mock_import.side_effect = ImportError("No module named 'nllm'")

        config = {"defaults": {}}
        runner = NLLMRunner(config)

        available, info = runner.check_nllm_available()

        assert available is False
        assert "not available" in info

    def test_validate_models(self):
        """Test model validation."""
        config = {"defaults": {}}
        runner = NLLMRunner(config)

        valid_models = [{"name": "model1", "options": ["-o", "temp", "0.7"]}, {"name": "model2"}]

        issues = runner.validate_models(valid_models)
        assert len(issues) == 0

        invalid_models = [
            {"options": ["--temp", "0.5"]},  # missing name
            {"name": "model2", "options": "invalid"},  # options not list
        ]

        issues = runner.validate_models(invalid_models)
        assert len(issues) == 2


def test_import_api():
    """Test that the main API functions can be imported."""
    from git_reviewer import ReviewResult, review_repository

    assert callable(review_repository)
    assert ReviewResult is not None


def test_version():
    """Test that version is available."""
    import git_reviewer

    assert hasattr(git_reviewer, "__version__")
    assert isinstance(git_reviewer.__version__, str)
