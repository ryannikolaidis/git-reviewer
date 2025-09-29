"""Python API for git-reviewer."""

from pathlib import Path
from typing import Any

from .config import get_models_config, load_config
from .context import build_repo_context, get_context_summary, resolve_context_paths
from .errors import GitReviewerError
from .git_integration import generate_diff, validate_and_prepare_repo
from .nllm_runner import NLLMRunner
from .template import format_prompt_for_nllm, populate_template


def review_repository(
    repo_path: str | None = None,
    models: list[str] | None = None,
    context_files: list[str] | None = None,
    output_dir: str | None = None,
    base_branch: str | None = None,
    context_lines: int | None = None,
    timeout: int | None = None,
    retries: int | None = None,
    config_override: dict[str, Any] | None = None,
    template_path: str | None = None,
):
    """
    Review git repository changes using AI models.

    Args:
        repo_path: Path to git repository (default: current directory)
        models: List of model names to use (default: all configured models)
        context_files: List of context file paths to include
        output_dir: Directory for review outputs
        base_branch: Base branch for diff (default: from config)
        context_lines: Number of context lines in git diff
        timeout: Timeout per model in seconds
        retries: Number of retries per model
        config_override: Dictionary to override configuration values
        template_path: Path to custom template file

    Returns:
        Raw nllm.NllmResults object

    Raises:
        GitReviewerError: For various error conditions
    """
    start_time = time.time()

    try:
        # Determine repository path
        if repo_path:
            repo_path_obj = Path(repo_path).resolve()
        else:
            repo_path_obj = Path.cwd()

        # Build configuration override
        override = config_override or {}

        if context_lines is not None:
            override.setdefault("git", {})["context_lines"] = context_lines
        if base_branch is not None:
            override.setdefault("git", {})["base_branch"] = base_branch
        if timeout is not None:
            override.setdefault("defaults", {})["timeout"] = timeout
        if retries is not None:
            override.setdefault("defaults", {})["retries"] = retries

        if template_path is not None:
            override.setdefault("paths", {})["template"] = template_path

        # Load configuration
        config = load_config(cwd=repo_path_obj, config_override=override)

        # Get model configurations
        model_configs = get_models_config(config, models)
        if not model_configs:
            raise GitReviewerError("No models configured. Please check your configuration.")

        # Validate and prepare repository
        git_config = config["git"]
        git_info, warning = validate_and_prepare_repo(repo_path_obj, git_config["base_branch"])

        # Generate diff
        diff_content = generate_diff(
            repo_path_obj, git_config["base_branch"], git_config["context_lines"], git_config["diff_scope"]
        )

        # Process context files
        context_file_paths = []
        repo_context = ""
        context_summary = None

        if context_files:
            context_file_paths = resolve_context_paths(context_files, repo_path_obj)
            repo_context = build_repo_context(context_file_paths, repo_path_obj)
            context_summary = get_context_summary(context_file_paths)

        # Load and populate template
        template_path_obj = Path(config["paths"]["template"])
        if not template_path_obj.is_absolute():
            # Try relative to package
            import git_reviewer

            package_dir = Path(git_reviewer.__file__).parent
            template_path_obj = package_dir / template_path_obj

        populated_template = populate_template(template_path_obj, repo_context, diff_content)
        prompt = format_prompt_for_nllm(populated_template)

        # Check nllm availability
        runner = NLLMRunner(config)
        nllm_available, nllm_info = runner.check_nllm_available()
        if not nllm_available:
            raise GitReviewerError(f"nllm not available: {nllm_info}")

        # Execute review (always in parallel)
        if output_dir:
            nllm_output_dir = Path(output_dir)
        else:
            # Check config for output directory (nllm-style), fallback to repo directory
            config_output_dir = config["defaults"].get("outdir")
            if config_output_dir:
                nllm_output_dir = Path(config_output_dir).expanduser()
            else:
                nllm_output_dir = repo_path_obj / "git-reviewer-results"

        # Return raw nllm results directly
        return runner.run_review(model_configs, prompt, nllm_output_dir, parallel=True)

    except Exception as e:
        if isinstance(e, GitReviewerError):
            raise
        else:
            raise GitReviewerError(f"Unexpected error during review: {e}")


def check_configuration(repo_path: str | None = None) -> dict[str, Any]:
    """
    Check git-reviewer configuration and dependencies.

    Args:
        repo_path: Path to git repository (default: current directory)

    Returns:
        Dictionary with configuration status information
    """
    if repo_path:
        repo_path_obj = Path(repo_path).resolve()
    else:
        repo_path_obj = Path.cwd()

    status = {
        "config_valid": False,
        "config_error": None,
        "models_count": 0,
        "nllm_available": False,
        "nllm_info": None,
        "git_repo_valid": False,
        "git_error": None,
    }

    # Check configuration
    config = None
    try:
        config = load_config(cwd=repo_path_obj)
        status["config_valid"] = True
        status["models_count"] = len(config.get("models", []))
    except Exception as e:
        status["config_error"] = str(e)

    # Check nllm if config is valid
    if status["config_valid"] and config is not None:
        try:
            runner = NLLMRunner(config)
            nllm_available, nllm_info = runner.check_nllm_available()
            status["nllm_available"] = nllm_available
            status["nllm_info"] = nllm_info
        except Exception as e:
            status["nllm_info"] = f"Error checking nllm: {e}"

    # Check git repository
    try:
        from .git_integration import validate_git_repo

        validate_git_repo(repo_path_obj)
        status["git_repo_valid"] = True
    except Exception as e:
        status["git_error"] = str(e)

    return status


def get_config_info(repo_path: str | None = None) -> dict[str, Any]:
    """
    Get detailed configuration information.

    Args:
        repo_path: Path to git repository (default: current directory)

    Returns:
        Dictionary with configuration details
    """
    if repo_path:
        repo_path_obj = Path(repo_path).resolve()
    else:
        repo_path_obj = Path.cwd()

    try:
        config = load_config(cwd=repo_path_obj)

        from .config import get_global_config_path, get_local_config_path

        return {
            "global_config_path": str(get_global_config_path()),
            "local_config_path": str(get_local_config_path(repo_path_obj)),
            "global_config_exists": get_global_config_path().exists(),
            "local_config_exists": get_local_config_path(repo_path_obj).exists(),
            "merged_config": config,
            "models": config.get("models", []),
            "defaults": config.get("defaults", {}),
            "git_settings": config.get("git", {}),
            "paths": config.get("paths", {}),
        }
    except Exception as e:
        return {"error": str(e)}


def create_config(
    global_config: bool = True, local_config: bool = False, repo_path: str | None = None
) -> dict[str, str]:
    """
    Create default configuration files.

    Args:
        global_config: Whether to create global configuration
        local_config: Whether to create local configuration
        repo_path: Path to git repository for local config (default: current directory)

    Returns:
        Dictionary with paths of created configuration files
    """
    created_files = {}

    if repo_path:
        repo_path_obj = Path(repo_path).resolve()
    else:
        repo_path_obj = Path.cwd()

    import yaml

    from .config import create_default_config, get_global_config_path, get_local_config_path

    if global_config:
        global_path = get_global_config_path()
        global_path.parent.mkdir(parents=True, exist_ok=True)

        default_config = create_default_config()
        with open(global_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)

        created_files["global"] = str(global_path)

    if local_config:
        local_path = get_local_config_path(repo_path_obj)

        # Create a minimal local config
        local_config_data = {"models": [{"name": "gpt-4", "options": ["-o", "temperature", "0.1"]}]}

        with open(local_path, "w") as f:
            yaml.dump(local_config_data, f, default_flow_style=False, indent=2)

        created_files["local"] = str(local_path)

    return created_files
