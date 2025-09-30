# git-reviewer

AI-powered code review tool that generates comprehensive reviews of git changes using multiple Large Language Models (LLMs) simultaneously.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

git-reviewer analyzes git repository changes and generates detailed code reviews using multiple AI models in parallel. It extracts git diffs, combines them with contextual information, and generates structured reviews that highlight issues, suggestions, and improvements.

### Key Features

- **Multi-Model Analysis**: Run reviews with multiple AI models simultaneously (GPT-4, Claude, Gemini, etc.)
- **Git Integration**: Automatically extracts diffs, commit information, and repository context
- **Template-Based Reviews**: Customizable review templates with structured output
- **Context-Aware**: Include additional context files to inform the review process
- **Flexible Configuration**: Global and local configuration with YAML-based settings
- **Rich Output**: Beautiful terminal output with JSON formatting and result summaries
- **Python API**: Use git-reviewer programmatically in your own tools
- **nllm Integration**: Built on the nllm library for robust multi-model execution
- **Comprehensive Change Explanation**: Each review includes an exhaustive explanation field that documents every change in the diff

## Installation

### Prerequisites

- Python 3.12 or higher
- Git
- [llm CLI tool](https://github.com/simonw/llm) with configured models
- pipx (recommended for global installation)

### Global Installation (Recommended)

```bash
# Install from source using pipx
git clone https://github.com/ryannikolaidis/git-reviewer.git
cd git-reviewer
pipx install .

# Or using the development Makefile
make install-package
```

### Local Development Installation

```bash
# Clone and set up development environment
git clone https://github.com/ryannikolaidis/git-reviewer.git
cd git-reviewer
make install-dev  # Installs with uv and sets up pre-commit hooks
```

### Model Setup

git-reviewer requires the `llm` CLI tool with configured models:

```bash
# Install llm
pip install llm

# Configure your API keys
llm keys set openai
llm keys set anthropic

# Verify models are available
llm models list
```
## Usage

### Quick Start

```bash
# Initialize configuration (creates ~/.git-reviewer/config.yaml)
git-reviewer init-config

# Run a basic review on current git changes
git-reviewer review

# Review with specific models
git-reviewer review --model gpt-4 --model claude-3-sonnet

# Review with additional context files
git-reviewer review --context-file src/config.py --context-file docs/api.md

# Check configuration and setup
git-reviewer check
```

### CLI Commands

```bash
# Review git changes (main command)
git-reviewer review [OPTIONS] [REPO_PATH]

# Initialize default configuration
git-reviewer init-config

# Check configuration and dependencies
git-reviewer check

# Show help
git-reviewer --help
```

### Review Command Options

- `--model`: Specify models to use (repeatable)
- `--context-file`: Include additional context files (repeatable)
- `--output-dir`: Directory for review outputs
- `--base-branch`: Base branch for diff (default: main)
- `--context-lines`: Number of context lines in git diff
- `--diff-scope`: Diff scope ('all' or 'committed')
- `--timeout`: Timeout per model in seconds (default: no timeout)
- `--retries`: Number of retries per model
- `--verbose`: Show detailed output

### Configuration

git-reviewer uses YAML configuration files with the following precedence:

1. Local: `.git-reviewer-config.yaml` (in repository)
2. Global: `~/.git-reviewer/config.yaml`

Example configuration:

```yaml
# Global configuration: ~/.git-reviewer/config.yaml
models:
  - name: gpt-4
    options: ["-o", "temperature", "0.1"]
  - name: claude-3-sonnet
    options: ["-o", "temperature", "0.0"]

defaults:
  retries: 1
  outdir: ~/code-reviews

git:
  context_lines: 3
  base_branch: main
  diff_scope: all
```

### Python API

git-reviewer can be used programmatically:

```python
from git_reviewer.api import review_repository

# Review current repository
nllm_results = review_repository()

# Review specific repository with options
nllm_results = review_repository(
    repo_path="/path/to/repo",
    models=["gpt-4", "claude-3-sonnet"],
    context_files=["src/config.py", "README.md"],
    output_dir="/tmp/reviews",
    base_branch="develop"
)

# Access results directly from nllm
for result in nllm_results.results:
    if result.status == "ok":
        print(f"Model: {result.model}")
        if hasattr(result, 'json') and result.json:
            # Use structured JSON output
            summary = result.json.get('summary', {})
            print(f"Issues found: {len(summary.get('issues', []))}")

            # Access the comprehensive explanation field
            explanation = result.json.get('explanation', {})
            print(f"Overview: {explanation.get('overview', 'N/A')}")
            print(f"Files analyzed: {len(explanation.get('detailed_analysis', []))}")
        else:
            # Use raw text output
            print(f"Review: {result.text[:200]}...")
```

## Review Output Format

git-reviewer generates structured JSON output with comprehensive information about your code changes:

### Key Output Sections

- **summary**: High-level assessment with readiness status and risk evaluation
- **blocking_issues**: Critical problems that must be fixed before merging
- **findings**: Non-blocking issues categorized by severity and domain
- **explanation**: **NEW** - Exhaustive documentation of every change in the diff
- **security_review**: Detailed security analysis and recommendations
- **file_summaries**: Per-file change summaries and risk assessments

### Explanation Field Details

The `explanation` field provides comprehensive documentation of all changes:

```json
{
  "explanation": {
    "overview": "High-level summary of all changes",
    "detailed_analysis": [
      {
        "file": "path/to/file.ext",
        "change_type": "added|modified|deleted|renamed|moved",
        "lines_added": 10,
        "lines_removed": 5,
        "purpose": "What this change accomplishes",
        "technical_details": "How the change works technically",
        "dependencies": ["List of affected components"],
        "business_logic": "Business reasoning behind the change",
        "implementation_notes": "Key implementation decisions"
      }
    ],
    "architectural_impact": "System-wide architectural effects",
    "data_flow_changes": "How data flows differently",
    "integration_points": "Affected external systems/APIs",
    "behavioral_changes": "Changes in user/system behavior",
    "rollback_considerations": "What's needed to undo changes"
  }
}
```

## Examples

### Basic Review

```bash
# Review current changes against main branch
cd /path/to/your/repo
git-reviewer review
```

### Advanced Review

```bash
# Comprehensive review with context and specific models
git-reviewer review \
    --model gpt-4 \
    --model claude-3-sonnet \
    --context-file src/core.py \
    --context-file docs/architecture.md \
    --base-branch develop \
    --output-dir ~/reviews \
    --verbose
```

### Integration with CI/CD

```yaml
# .github/workflows/code-review.yml
name: AI Code Review
on: [pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install git-reviewer
        run: pipx install git+https://github.com/ryannikolaidis/git-reviewer.git
      - name: Run AI review
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          git-reviewer review --base-branch origin/main --output-dir ./review-results
      - name: Upload review results
        uses: actions/upload-artifact@v3
        with:
          name: ai-review
          path: ./review-results
```

## Development

### Setup

```bash
# Clone and install development environment
git clone https://github.com/ryannikolaidis/git-reviewer.git
cd git-reviewer
make install-dev  # Sets up uv environment and pre-commit hooks
```

### Development Commands

```bash
# Code quality
make lint          # Run ruff and mypy
make tidy          # Auto-fix formatting with ruff and black
make check         # Run all quality checks

# Testing
make test          # Run pytest
make test-cov      # Run tests with coverage

# Development workflow
make version-dev   # Bump development version
make build         # Build package
make install-package  # Install globally with pipx

# Documentation
make docs          # Build Sphinx documentation
make docs-serve    # Build and serve docs locally
```

### Architecture

git-reviewer follows a modular architecture:

- **CLI Layer** (`cli.py`): Typer-based command interface
- **API Layer** (`api.py`): Python API for programmatic usage
- **Core Components**:
  - `git_integration.py`: Git repository operations
  - `nllm_runner.py`: nllm integration for multi-model execution
  - `template.py`: Review template processing
  - `config.py`: Configuration management
  - `context.py`: Context file processing

See `docs/design/` for detailed architectural documentation.

## Troubleshooting

### Common Issues

**"nllm not available" error**
```bash
# Ensure llm is installed and configured
pip install llm
llm models list
```

**"No models configured" error**
```bash
# Initialize configuration
git-reviewer init-config
# Edit ~/.git-reviewer/config.yaml to add your models
```

**Permission errors with git**
```bash
# Ensure you're in a git repository
git status
# Check git configuration
git config --list
```

### Model Configuration

Different models require different option formats:

```yaml
models:
  # OpenAI models
  - name: gpt-4
    options: ["-o", "temperature", "0.1", "-o", "max_tokens", "4000"]

  # Anthropic models
  - name: claude-3-sonnet
    options: ["-o", "temperature", "0.0", "--system", "You are a code reviewer"]

  # Google models
  - name: gemini-pro
    options: ["-o", "temperature", "0.2"]

defaults:
  retries: 1
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `make check`
5. Commit your changes: `git commit -am 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Related Projects

- [nllm](https://github.com/ryannikolaidis/nllm) - Multi-model LLM execution library
- [llm](https://github.com/simonw/llm) - Command-line tool for interacting with LLMs
