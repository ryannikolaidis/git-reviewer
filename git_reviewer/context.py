"""Context file handling and aggregation for git-reviewer."""

from pathlib import Path

from .errors import ContextError

MAX_FILE_SIZE_MB = 10
MAX_TOTAL_SIZE_MB = 50


def validate_context_file(file_path: Path) -> None:
    """Validate that a context file can be safely read."""
    if not file_path.exists():
        raise ContextError(f"Context file does not exist: {file_path}")

    if not file_path.is_file():
        raise ContextError(f"Context path is not a file: {file_path}")

    # Check file size
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise ContextError(
            f"Context file too large: {file_path} ({file_size_mb:.1f}MB > {MAX_FILE_SIZE_MB}MB)"
        )


def is_binary_file(file_path: Path) -> bool:
    """Check if a file appears to be binary by looking for null bytes."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)  # Read first 1KB
            return b"\x00" in chunk
    except Exception:
        return True  # Assume binary if we can't read it


def read_context_file(file_path: Path) -> str:
    """Read a single context file and return its content with header."""
    validate_context_file(file_path)

    # Handle binary files
    if is_binary_file(file_path):
        return f"\n--- {file_path} ---\n[Binary file - content not included]\n"

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Add file header
        formatted_content = f"\n--- {file_path} ---\n{content}\n"
        return formatted_content

    except UnicodeDecodeError:
        return f"\n--- {file_path} ---\n[Binary or non-UTF-8 file - content not included]\n"
    except Exception as e:
        raise ContextError(f"Failed to read context file {file_path}: {e}")


def build_repo_context(context_files: list[Path], base_path: Path | None = None) -> str:
    """Aggregate content from specified files for template variable."""
    if not context_files:
        return ""

    # Calculate total size before reading
    total_size_mb = 0
    for file_path in context_files:
        if file_path.exists() and file_path.is_file():
            total_size_mb += file_path.stat().st_size / (1024 * 1024)

    if total_size_mb > MAX_TOTAL_SIZE_MB:
        raise ContextError(
            f"Total context files too large: {total_size_mb:.1f}MB > {MAX_TOTAL_SIZE_MB}MB"
        )

    context_parts = []
    processed_files = set()

    for file_path in context_files:
        # Resolve relative paths
        if base_path and not file_path.is_absolute():
            resolved_path = base_path / file_path
        else:
            resolved_path = file_path.resolve()

        # Avoid duplicates
        if resolved_path in processed_files:
            continue
        processed_files.add(resolved_path)

        try:
            file_content = read_context_file(resolved_path)
            context_parts.append(file_content)
        except ContextError as e:
            # Include error information in context
            error_content = f"\n--- {resolved_path} ---\n[Error reading file: {e}]\n"
            context_parts.append(error_content)

    if not context_parts:
        return ""

    # Join all parts with separators
    return "\n".join(context_parts)


def resolve_context_paths(context_files: list[str], base_path: Path | None = None) -> list[Path]:
    """Convert string paths to resolved Path objects."""
    if base_path is None:
        base_path = Path.cwd()

    resolved_paths = []
    for file_path_str in context_files:
        file_path = Path(file_path_str)

        if file_path.is_absolute():
            resolved_paths.append(file_path)
        else:
            resolved_paths.append(base_path / file_path)

    return resolved_paths


def get_context_summary(context_files: list[Path]) -> dict:
    """Get summary information about context files."""
    summary = {
        "total_files": len(context_files),
        "total_size_mb": 0.0,
        "readable_files": 0,
        "binary_files": 0,
        "missing_files": 0,
        "error_files": 0,
    }

    for file_path in context_files:
        if not file_path.exists():
            summary["missing_files"] += 1
            continue

        if not file_path.is_file():
            summary["error_files"] += 1
            continue

        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        summary["total_size_mb"] += file_size_mb

        if is_binary_file(file_path):
            summary["binary_files"] += 1
        else:
            summary["readable_files"] += 1

    summary["total_size_mb"] = round(summary["total_size_mb"], 2)
    return summary
