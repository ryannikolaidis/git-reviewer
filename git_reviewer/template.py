"""Template processing and variable substitution for git-reviewer."""

import string
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from .errors import TemplateError


class SafeTemplate(string.Template):
    """Template class that doesn't raise KeyError for missing substitutions."""

    def safe_substitute(self, mapping: Mapping[str, Any] = {}, /, **kwargs: Any) -> str:
        """Substitute variables, leaving unmatched variables unchanged."""
        try:
            return super().safe_substitute(mapping, **kwargs)
        except ValueError as e:
            raise TemplateError(f"Template substitution error: {e}")


def load_template(template_path: Path) -> dict[str, str]:
    """Load template from YAML file."""
    if not template_path.exists():
        raise TemplateError(f"Template file not found: {template_path}")

    try:
        with open(template_path, encoding="utf-8") as f:
            template_data = yaml.safe_load(f)

        if not isinstance(template_data, dict):
            raise TemplateError(f"Template file must contain a YAML dictionary: {template_path}")

        # Validate required keys
        required_keys = ["system", "prompt"]
        missing_keys = [key for key in required_keys if key not in template_data]
        if missing_keys:
            raise TemplateError(f"Template missing required keys: {missing_keys}")

        # Ensure values are strings
        for key, value in template_data.items():
            if not isinstance(value, str):
                raise TemplateError(f"Template key '{key}' must be a string, got {type(value)}")

        return template_data

    except yaml.YAMLError as e:
        raise TemplateError(f"Invalid YAML in template file {template_path}: {e}")
    except Exception as e:
        raise TemplateError(f"Failed to load template {template_path}: {e}")


def substitute_variables(template_content: str, variables: dict[str, str]) -> str:
    """Substitute template variables in content."""
    if not template_content:
        return template_content

    try:
        template = SafeTemplate(template_content)
        return template.safe_substitute(variables)
    except Exception as e:
        raise TemplateError(f"Template variable substitution failed: {e}")


def populate_template(
    template_path: Path, repo_context: str, diff: str, additional_vars: dict[str, str] | None = None
) -> dict[str, str]:
    """Load template and populate with variables."""
    # Load template
    template_data = load_template(template_path)

    # Prepare variables
    variables = {
        "repo_context": repo_context,
        "diff": diff,
    }

    # Add any additional variables
    if additional_vars:
        variables.update(additional_vars)

    # Substitute variables in each template section
    populated_template = {}
    for key, content in template_data.items():
        try:
            populated_content = substitute_variables(content, variables)
            populated_template[key] = populated_content
        except TemplateError as e:
            raise TemplateError(f"Failed to populate template section '{key}': {e}")

    return populated_template


def format_prompt_for_nllm(populated_template: dict[str, str]) -> str:
    """Format populated template for nllm consumption."""
    # nllm expects a single prompt string
    # Combine system and prompt sections
    system_content = populated_template.get("system", "").strip()
    prompt_content = populated_template.get("prompt", "").strip()

    if not prompt_content:
        raise TemplateError("Template must have non-empty 'prompt' section")

    if system_content:
        # Combine system and prompt with clear separation
        formatted_prompt = f"{system_content}\n\n{prompt_content}"
    else:
        formatted_prompt = prompt_content

    return formatted_prompt


def validate_template_variables(template_content: str, required_vars: list | None = None) -> list:
    """Check what variables are referenced in a template."""
    if required_vars is None:
        required_vars = ["repo_context", "diff"]

    # Extract variable names from template
    # This is a simplified approach - get identifiers from the template pattern
    import re

    pattern = r"\$(\w+)|\$\{(\w+)\}"
    found_vars = set()

    for match in re.finditer(pattern, template_content):
        var_name = match.group(1) or match.group(2)
        found_vars.add(var_name)

    # Check for missing required variables
    missing_vars = [var for var in required_vars if var not in found_vars]
    return missing_vars


def get_template_info(template_path: Path) -> dict[str, Any]:
    """Get information about a template file."""
    if not template_path.exists():
        return {"exists": False, "error": "Template file not found"}

    try:
        template_data = load_template(template_path)

        info = {
            "exists": True,
            "sections": list(template_data.keys()),
            "variables_by_section": {},
            "total_length": 0,
        }

        for section, content in template_data.items():
            # Find variables in this section
            import re

            pattern = r"\$(\w+)|\$\{(\w+)\}"
            found_vars = set()
            for match in re.finditer(pattern, content):
                var_name = match.group(1) or match.group(2)
                found_vars.add(var_name)

            info["variables_by_section"][section] = sorted(found_vars)
            info["total_length"] += len(content)

        return info

    except Exception as e:
        return {"exists": True, "error": str(e)}


def create_minimal_template() -> str:
    """Create a minimal template for testing purposes."""
    return """system: |
  You are a code reviewer.

prompt: |
  Please review the following changes:

  Repository context:
  $repo_context

  Diff to review:
  $diff

  Provide your review in JSON format.
"""
