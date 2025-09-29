"""Data models and result structures for git-reviewer."""

from dataclasses import dataclass
from typing import Any, Dict, List


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
class ReviewResult:
    """Result from running git-reviewer across multiple models."""

    success: bool
    results: Dict[str, Any]  # nllm output per model
    errors: Dict[str, str]   # Error messages per failed model
    metadata: Dict[str, Any] # Git info, timing, config used

    def get_successful_reviews(self) -> Dict[str, Any]:
        """Return only successful model results."""
        return {model: result for model, result in self.results.items()
                if model not in self.errors}

    def get_failed_models(self) -> List[str]:
        """Return list of models that failed."""
        return list(self.errors.keys())

    def get_summary(self) -> Dict[str, Any]:
        """Return summary of the review results."""
        return {
            "total_models": len(self.results) + len(self.errors),
            "successful_models": len(self.results) - len(self.errors),
            "failed_models": len(self.errors),
            "success_rate": (len(self.results) - len(self.errors)) / (len(self.results) + len(self.errors)) if (len(self.results) + len(self.errors)) > 0 else 0.0
        }

    def has_any_success(self) -> bool:
        """Check if at least one model succeeded."""
        return len(self.get_successful_reviews()) > 0
