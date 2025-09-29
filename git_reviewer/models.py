"""Data models and result structures for git-reviewer."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ReviewResult:
    """Result from a git-reviewer execution."""

    success: bool
    results: dict[str, Any]  # nllm output per model
    errors: dict[str, str]  # Error messages per failed model
    metadata: dict[str, Any]  # Git info, timing, config used

    def get_successful_reviews(self) -> dict[str, Any]:
        """Return only successful model results."""
        return {
            name: result for name, result in self.results.items() if result.get("success", False)
        }

    def get_failed_models(self) -> list[str]:
        """Return list of models that failed."""
        return list(self.errors.keys())

    def has_any_success(self) -> bool:
        """Check if at least one model succeeded."""
        return len(self.get_successful_reviews()) > 0

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics of the review."""
        successful = self.get_successful_reviews()
        return {
            "total_models": len(self.results) + len(self.errors),
            "successful_models": len(successful),
            "failed_models": len(self.errors),
            "success_rate": len(successful) / max(1, len(self.results) + len(self.errors)),
            "has_results": len(successful) > 0,
        }


@dataclass
class GitInfo:
    """Git repository information."""

    current_branch: str
    base_branch: str
    merge_base: str
    head_commit: str
    commit_range: str
    stats: dict[str, int]  # files, insertions, deletions
    diff_stats: str


@dataclass
class ContextSummary:
    """Summary of context files processed."""

    total_files: int
    total_size_mb: float
    readable_files: int
    binary_files: int
    missing_files: int
    error_files: int

    @property
    def has_issues(self) -> bool:
        """Check if there were any issues with context files."""
        return self.missing_files > 0 or self.error_files > 0


@dataclass
class ReviewConfig:
    """Configuration for a review run."""

    repo_path: Path
    models: list[str]
    context_files: list[Path]
    base_branch: str
    context_lines: int
    template_path: Path
    output_dir: Path | None = None
    parallel: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "repo_path": str(self.repo_path),
            "models": self.models,
            "context_files": [str(f) for f in self.context_files],
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "base_branch": self.base_branch,
            "context_lines": self.context_lines,
            "parallel": self.parallel,
            "template_path": str(self.template_path),
        }
