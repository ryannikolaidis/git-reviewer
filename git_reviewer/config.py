"""Configuration loading and validation for git-reviewer."""

from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigurationError

DEFAULT_CONFIG = {
    "models": [],
    "defaults": {
        "parallel": 3,
        "timeout": 120,
        "retries": 1,
    },
    "git": {
        "context_lines": 3,
        "base_branch": "main",
        "diff_scope": "all",  # "all" (committed+staged+unstaged) or "committed" (committed only)
    },
    "paths": {
        "template": "review.template.yml",
        "output_dir": None,
    },
}


def get_global_config_path() -> Path:
    """Get the path to the global configuration file."""
    return Path.home() / ".git-reviewer" / "config.yaml"


def get_local_config_path(cwd: Path | None = None) -> Path:
    """Get the path to the local configuration file."""
    if cwd is None:
        cwd = Path.cwd()
    return cwd / ".git-reviewer-config.yaml"


def load_yaml_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from a YAML file."""
    if not config_path.exists():
        return {}

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return config or {}
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in config file {config_path}: {e}")
    except Exception as e:
        raise ConfigurationError(f"Failed to read config file {config_path}: {e}")


def deep_merge_config(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two configuration dictionaries."""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_config(result[key], value)
        else:
            result[key] = value

    return result


def validate_config(config: dict[str, Any]) -> None:
    """Validate configuration structure and values."""
    # Check required top-level keys
    required_keys = ["models", "defaults", "git", "paths"]
    for key in required_keys:
        if key not in config:
            raise ConfigurationError(f"Missing required configuration key: {key}")

    # Validate models
    models = config["models"]
    if not isinstance(models, list):
        raise ConfigurationError("'models' must be a list")

    for i, model in enumerate(models):
        if not isinstance(model, dict):
            raise ConfigurationError(f"Model at index {i} must be a dictionary")

        if "name" not in model:
            raise ConfigurationError(f"Model at index {i} missing required 'name' field")

        if "options" in model and not isinstance(model["options"], list):
            raise ConfigurationError(f"Model '{model['name']}' options must be a list")

    # Validate defaults
    defaults = config["defaults"]
    if not isinstance(defaults, dict):
        raise ConfigurationError("'defaults' must be a dictionary")

    for key in ["parallel", "timeout", "retries"]:
        if key in defaults:
            value = defaults[key]
            if not isinstance(value, int) or value < 0:
                raise ConfigurationError(f"'defaults.{key}' must be a non-negative integer")

    # Validate git settings
    git_config = config["git"]
    if not isinstance(git_config, dict):
        raise ConfigurationError("'git' must be a dictionary")

    if "context_lines" in git_config:
        value = git_config["context_lines"]
        if not isinstance(value, int) or value < 0:
            raise ConfigurationError("'git.context_lines' must be a non-negative integer")

    if "base_branch" in git_config:
        value = git_config["base_branch"]
        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError("'git.base_branch' must be a non-empty string")


def load_config(
    cwd: Path | None = None, config_override: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Load and merge configuration from global and local sources."""
    # Start with default configuration
    config = DEFAULT_CONFIG.copy()

    # Load global configuration
    global_config_path = get_global_config_path()
    if global_config_path.exists():
        global_config = load_yaml_config(global_config_path)
        config = deep_merge_config(config, global_config)

    # Load local configuration
    local_config_path = get_local_config_path(cwd)
    if local_config_path.exists():
        local_config = load_yaml_config(local_config_path)
        config = deep_merge_config(config, local_config)

    # Apply any runtime overrides
    if config_override:
        config = deep_merge_config(config, config_override)

    # Validate final configuration
    validate_config(config)

    return config


def get_models_config(
    config: dict[str, Any], model_names: list[str] | None = None
) -> list[dict[str, Any]]:
    """Get model configurations, optionally filtered by model names."""
    all_models = config["models"]

    if model_names is None:
        return all_models

    # Filter models by requested names
    filtered_models = []
    available_names = {model["name"] for model in all_models}

    for name in model_names:
        if name not in available_names:
            raise ConfigurationError(
                f"Model '{name}' not found in configuration. Available models: {sorted(available_names)}"
            )

        for model in all_models:
            if model["name"] == name:
                filtered_models.append(model)
                break

    return filtered_models


def create_default_config() -> dict[str, Any]:
    """Create a default configuration file template."""
    return {
        "models": [
            {
                "name": "gpt-4.1",
                "options": ["-o", "temperature", "0.7", "--system", "You are a helpful and concise assistant"],
            },
            {
                "name": "claude-opus-4.1",
                "options": ["-o", "temperature", "0.2", "--system", "Be precise and analytical"],
            },
        ],
        "defaults": {
            "parallel": 3,
            "timeout": 120,
            "retries": 1,
            "outdir": None,  # Use nllm-style outdir
        },
        "git": {
            "context_lines": 3,
            "base_branch": "main",
        },
        "paths": {
            "template": "review.template.yml",
        },
    }
