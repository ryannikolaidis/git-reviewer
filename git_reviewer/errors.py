"""Exception classes and error handling for git-reviewer."""


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


class TemplateError(GitReviewerError):
    """Template processing and variable substitution errors."""

    pass
