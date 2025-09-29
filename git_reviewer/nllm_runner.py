"""nllm integration and command execution for git-reviewer."""

from pathlib import Path
from typing import Any

from .errors import NLLMError


class NLLMRunner:
    """Handles nllm execution using the Python API."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.defaults = config.get("defaults", {})

    def _prepare_model_options(self, model_config: dict[str, str]) -> list[str]:
        """Convert model options to nllm format."""
        model_name = model_config["name"]
        model_options = model_config.get("options", [])

        if not model_options:
            return []

        # Convert options list to nllm format: model:option1:option2:...
        option_str = f"{model_name}:" + ":".join(model_options)
        return [option_str]

    def run_review(
        self,
        models: list[dict[str, str]],
        prompt: str,
        output_dir: Path | None = None,
    ):
        """Execute review using nllm Python API."""
        if not models:
            raise NLLMError("No models configured for review")

        if not prompt.strip():
            raise NLLMError("Empty prompt provided")

        try:
            # Import nllm here to avoid import errors if not available
            import nllm
        except ImportError:
            raise NLLMError("nllm package not available. Please install nllm.")

        # Prepare models list
        cli_models = [model["name"] for model in models]

        # Prepare model options
        cli_model_options = []
        for model in models:
            cli_model_options.extend(self._prepare_model_options(model))

        try:
            # Execute nllm
            # Let nllm manage output directory to avoid double-nesting
            if output_dir:
                # User specified output dir - use it directly as nllm's outdir
                nllm_outdir = str(output_dir)
            else:
                # No output dir specified - let nllm create its own
                nllm_outdir = None

            return nllm.run(
                cli_models=cli_models,
                cli_model_options=cli_model_options,
                outdir=nllm_outdir,
                timeout=self.defaults.get("timeout", 120),
                retries=self.defaults.get("retries", 0),
                stream=False,  # Disable streaming for API usage
                quiet=True,  # Reduce console output
                llm_args=[prompt],
            )

        except Exception as e:
            raise NLLMError(f"Failed to execute nllm review: {e}")

    def check_nllm_available(self) -> tuple[bool, str]:
        """Check if nllm Python API is available."""
        try:
            import nllm

            return True, f"nllm Python API available (version: {nllm.__version__})"
        except ImportError:
            return False, "nllm Python API not available. Please install nllm package."
        except Exception as e:
            return False, f"Error checking nllm: {e}"

    def validate_models(self, models: list[dict[str, str]]) -> list[str]:
        """Validate that models are properly configured."""
        issues = []

        for i, model in enumerate(models):
            if "name" not in model:
                issues.append(f"Model at index {i} missing 'name' field")
                continue

            model_name = model["name"]
            if not isinstance(model_name, str) or not model_name.strip():
                issues.append(f"Model at index {i} has invalid name: {model_name}")

            if "options" in model:
                options = model["options"]
                if not isinstance(options, list):
                    issues.append(
                        f"Model '{model_name}' options must be a list, got {type(options)}"
                    )
                elif not all(isinstance(opt, str) for opt in options):
                    issues.append(f"Model '{model_name}' options must be strings")

        return issues
