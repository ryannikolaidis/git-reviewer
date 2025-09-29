# Git Reviewer Design Document

## Overview

Git Reviewer is a CLI tool and Python library that provides automated code review using multiple LLM models. It integrates with git repositories to extract diffs and uses the nllm library to orchestrate reviews across multiple AI models.

## Architecture

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Interface │    │   Python API     │    │ Configuration   │
│   (typer)       │────│   (core logic)   │────│ Management      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Git Integration  │────│ Context Builder │
                       │ (diff generation)│    │ (file aggregator│
                       └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ nllm Integration │────│ Template Engine │
                       │ (model orchestr.)│    │ (prompt builder)│
                       └──────────────────┘    └─────────────────┘
```

## Configuration System

### Configuration File Locations

1. **Global Config**: `~/.git-reviewer/config.yaml`
2. **Local Override**: `./.git-reviewer-config.yaml` (in current working directory)

Local config takes precedence over global config, with deep merging for nested structures.

### Configuration Schema

```yaml
# ~/.git-reviewer/config.yaml
models:
  - name: "gpt-4.1"
    options: ["-o", "temperature", "0.7", "--system", "You are a helpful and concise assistant"]
  - name: "gemini-2.5-flash-preview-05-20"
    options: ["-o", "temperature", "0.3"]
  - name: "claude-opus-4.1"
    options: ["-o", "temperature", "0.2", "--system", "Be precise and analytical"]

defaults:
  parallel: 3
  timeout: 120
  retries: 1

git:
  context_lines: 3  # Number of context lines for git diff
  base_branch: "main"  # Default base branch for diff

paths:
  template: "review.template.yml"  # Path to prompt template
  output_dir: null  # Default output directory (null = use nllm default)
```

### Configuration Loading Strategy

```python
def load_config() -> dict:
    """Load and merge configuration from global and local sources."""
    # 1. Load global config from ~/.git-reviewer/config.yaml
    # 2. Load local config from ./.git-reviewer-config.yaml
    # 3. Deep merge local over global
    # 4. Validate schema
    # 5. Return merged config
```

## Git Integration

### Repository Validation

```python
def validate_git_repo(path: Path) -> None:
    """Validate that path is a git repository with required structure."""
    # Check .git directory exists
    # Verify git command available
    # Validate base branch exists (default: main)
    # Check for uncommitted changes (warn, don't block)
```

### Diff Generation

```python
def generate_diff(repo_path: Path, base_branch: str, context_lines: int) -> str:
    """Generate git diff from base branch with configurable context."""
    # Find merge base with base branch
    # Generate diff with specified context lines
    # Handle binary files appropriately
    # Return unified diff format
```

## Context Management

### Repository Context Builder

```python
def build_repo_context(context_files: List[Path]) -> str:
    """Aggregate content from specified files for template variable."""
    # Read and combine all context files
    # Add file path headers for clarity
    # Handle binary files gracefully
    # Return formatted context string
```

### Template Variable Population

```python
def populate_template(template_path: Path, repo_context: str, diff: str) -> str:
    """Replace template variables with actual content."""
    # Load template from YAML
    # Replace $repo_context with aggregated file content
    # Replace $diff with git diff output
    # Return populated prompt
```

## nllm Integration

### Model Orchestration

```python
class NLLMRunner:
    def __init__(self, config: dict):
        self.config = config

    def run_review(self, prompt: str, output_dir: Optional[Path] = None) -> dict:
        """Execute review using configured models via nllm."""
        # Build nllm command arguments from config
        # Handle parallel execution settings
        # Pass through output directory if specified
        # Execute nllm with populated prompt
        # Return results with model attribution
```

### Command Construction

```python
def build_nllm_command(model_config: dict, prompt: str, output_dir: Optional[Path]) -> List[str]:
    """Build nllm command from model configuration."""
    # Base command: ["nllm"]
    # Add model-specific options
    # Add global defaults (timeout, retries, parallel)
    # Add output directory if specified
    # Add prompt as final argument or stdin
```

## Error Handling

### Error Types

```python
class GitReviewerError(Exception):
    """Base exception for git-reviewer errors."""
    pass

class GitRepositoryError(GitReviewerError):
    """Git repository validation or operation errors."""
    pass

class ConfigurationError(GitReviewerError):
    """Configuration loading or validation errors."""
    pass

class NLLMError(GitReviewerError):
    """nllm execution errors."""
    pass

class ContextError(GitReviewerError):
    """Context file reading or processing errors."""
    pass
```

### Error Handling Strategy

- **CLI Usage**: Catch all exceptions, display user-friendly messages, exit with appropriate codes
- **API Usage**: Let exceptions propagate with detailed messages for programmatic handling
- **Partial Failures**: Continue with successful models, report failures clearly

## CLI Interface

### Main Command

```bash
git-reviewer [OPTIONS] [REPO_PATH]
```

### Command Options

```bash
Options:
  --config PATH              Path to configuration file
  --model TEXT               Model name to use (can be specified multiple times)
  --output-dir PATH          Directory for review outputs
  --context-file PATH        Context files to include (multiple allowed)
  --context-lines INTEGER    Number of context lines in git diff [default: 3]
  --base-branch TEXT         Base branch for diff [default: main]
  --timeout INTEGER          Timeout per model in seconds
  --retries INTEGER          Number of retries per model
  --help                     Show this message and exit
```

### Command Examples

```bash
# Basic usage - review current directory
git-reviewer

# Specify repository path
git-reviewer /path/to/repo

# Include context files
git-reviewer --context-files README.md --context-files docs/architecture.md

# Use specific models only
git-reviewer --model gpt-4.1 --model claude-opus-4.1

# Custom output directory
git-reviewer --output-dir ./reviews/$(date +%Y%m%d_%H%M%S)

# Override context lines for more/less context
git-reviewer --context-lines 5
```

## Python API

### Core API

```python
from git_reviewer import review_repository

# Basic usage
results = review_repository()

# Full configuration
results = review_repository(
    repo_path="/path/to/repo",
    models=["gpt-4.1", "claude-opus-4.1"],
    context_files=["README.md", "docs/api.md"],
    output_dir="./reviews",
    config_override={
        "git": {"context_lines": 5},
        "defaults": {"parallel": 2}
    }
)
```

### API Response Format

```python
class ReviewResult:
    success: bool
    results: Dict[str, Any]  # nllm output per model
    errors: Dict[str, str]   # Error messages per failed model
    metadata: Dict[str, Any] # Git info, timing, config used

    def get_successful_reviews(self) -> Dict[str, Any]:
        """Return only successful model results."""

    def get_failed_models(self) -> List[str]:
        """Return list of models that failed."""
```

## Implementation Plan

### Phase 1: Core Infrastructure
1. Configuration system with YAML loading and validation
2. Git repository validation and diff generation
3. Template variable population system
4. Basic error handling framework

### Phase 2: nllm Integration
1. nllm command construction and execution
2. Result parsing and attribution
3. Parallel execution handling
4. Error recovery and partial success handling

### Phase 3: CLI Interface
1. Typer-based command structure
2. Argument parsing and validation
3. User-friendly error messages
4. Output formatting and display

### Phase 4: Python API
1. Programmatic interface design
2. Result object structure
3. Configuration override system
4. API documentation

### Phase 5: Testing & Documentation
1. Unit tests for all components
2. Integration tests with git repositories
3. CLI usage examples and documentation
4. API reference documentation

## File Structure

```
git_reviewer/
├── __init__.py              # Package initialization and main API
├── cli.py                   # CLI interface (typer commands)
├── config.py                # Configuration loading and validation
├── git_integration.py       # Git operations and diff generation
├── context.py               # Context file handling and aggregation
├── nllm_runner.py          # nllm integration and execution
├── template.py             # Template processing and variable substitution
├── errors.py               # Exception classes and error handling
├── models.py               # Data models and result structures
└── review.template.yml     # Default review prompt template
```

## Security Considerations

1. **File Access**: Validate all file paths to prevent directory traversal
2. **Command Injection**: Sanitize all inputs passed to shell commands
3. **Sensitive Data**: Ensure no secrets leak into review outputs or logs
4. **Resource Limits**: Implement reasonable limits on context file sizes
5. **Configuration Validation**: Strict schema validation for all config inputs

## Performance Considerations

1. **Large Diffs**: Implement chunking strategy for very large diffs
2. **Context Files**: Limit total context size to prevent token limit issues
3. **Parallel Execution**: Respect system resources and API rate limits
4. **Caching**: Consider caching git operations for repeated runs
5. **Memory Usage**: Stream large files rather than loading entirely in memory

## Future Enhancements

1. **Custom Templates**: Support for user-defined prompt templates
2. **Review History**: Track and compare reviews over time
3. **Integration Hooks**: Pre-commit hooks, CI/CD integration
4. **Interactive Mode**: Allow user to refine context and re-run
5. **Review Aggregation**: Combine multiple model outputs intelligently