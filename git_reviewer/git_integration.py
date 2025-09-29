"""Git operations and diff generation for git-reviewer."""

import subprocess
from pathlib import Path

from .errors import GitRepositoryError


def validate_git_repo(path: Path) -> None:
    """Validate that path is a git repository with required structure."""
    if not path.exists():
        raise GitRepositoryError(f"Path does not exist: {path}")

    if not path.is_dir():
        raise GitRepositoryError(f"Path is not a directory: {path}")

    # Check if .git directory exists
    git_dir = path / ".git"
    if not git_dir.exists():
        raise GitRepositoryError(f"Not a git repository: {path}")

    # Verify git command is available
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True, cwd=path)
    except subprocess.CalledProcessError:
        raise GitRepositoryError("Git command not available")
    except FileNotFoundError:
        raise GitRepositoryError("Git command not found")


def validate_base_branch(repo_path: Path, base_branch: str) -> None:
    """Validate that the base branch exists in the repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", f"{base_branch}"],
            capture_output=True,
            check=True,
            cwd=repo_path,
            text=True,
        )
    except subprocess.CalledProcessError:
        # Check if branch exists remotely
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", f"origin/{base_branch}"],
                capture_output=True,
                check=True,
                cwd=repo_path,
                text=True,
            )
            raise GitRepositoryError(
                f"Base branch '{base_branch}' exists remotely but not locally. "
                f"Run 'git checkout {base_branch}' or 'git fetch origin {base_branch}'"
            )
        except subprocess.CalledProcessError:
            raise GitRepositoryError(f"Base branch '{base_branch}' does not exist")


def get_current_branch(repo_path: Path) -> str:
    """Get the current branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            check=True,
            cwd=repo_path,
            text=True,
        )
        branch_name = result.stdout.strip()
        if not branch_name:
            # Fallback for detached HEAD or older git versions
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                check=True,
                cwd=repo_path,
                text=True,
            )
            branch_name = result.stdout.strip()
            if branch_name == "HEAD":
                raise GitRepositoryError("Repository is in detached HEAD state")
        return branch_name
    except subprocess.CalledProcessError as e:
        raise GitRepositoryError(f"Failed to get current branch: {e}")


def get_merge_base(repo_path: Path, base_branch: str) -> str:
    """Find the merge base between current HEAD and base branch."""
    try:
        result = subprocess.run(
            ["git", "merge-base", "HEAD", base_branch],
            capture_output=True,
            check=True,
            cwd=repo_path,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            raise GitRepositoryError(
                f"No merge base found between current branch and '{base_branch}'. "
                "Are you on a branch that diverged from the base branch?"
            )
        raise GitRepositoryError(f"Failed to find merge base: {e}")


def check_uncommitted_changes(repo_path: Path) -> tuple[bool, str]:
    """Check for uncommitted changes and return status with message."""
    try:
        # Check for staged changes
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=repo_path, capture_output=True
        )
        has_staged = result.returncode != 0

        # Check for unstaged changes
        result = subprocess.run(["git", "diff", "--quiet"], cwd=repo_path, capture_output=True)
        has_unstaged = result.returncode != 0

        # Check for untracked files
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        has_untracked = bool(result.stdout.strip())

        if has_staged or has_unstaged or has_untracked:
            warning_parts = []
            if has_staged:
                warning_parts.append("staged changes")
            if has_unstaged:
                warning_parts.append("unstaged changes")
            if has_untracked:
                warning_parts.append("untracked files")

            message = f"Repository has {', '.join(warning_parts)}. These will not be included in the review."
            return True, message

        return False, "Repository is clean"

    except subprocess.CalledProcessError as e:
        raise GitRepositoryError(f"Failed to check repository status: {e}")


def generate_diff(
    repo_path: Path, base_branch: str, context_lines: int = 3, diff_scope: str = "all"
) -> str:
    """Generate git diff from merge base with base branch.

    Args:
        repo_path: Path to the git repository
        base_branch: Base branch for comparison
        context_lines: Number of context lines in diff
        diff_scope: Scope of changes to include - "all" (committed+staged+unstaged) or "committed" (committed only)
    """
    # Find merge base
    merge_base = get_merge_base(repo_path, base_branch)

    diff_sections = []

    try:
        # Always include committed changes
        result = subprocess.run(
            ["git", "diff", f"--unified={context_lines}", f"{merge_base}..HEAD"],
            capture_output=True,
            check=True,
            cwd=repo_path,
            text=True,
        )
        committed_diff = result.stdout.strip()
        if committed_diff:
            if diff_scope == "all":
                diff_sections.append("# === COMMITTED CHANGES ===")
            diff_sections.append(committed_diff)

        # Include staged and unstaged changes only if scope is "all"
        if diff_scope == "all":
            # 2. Staged changes (--cached HEAD)
            result = subprocess.run(
                ["git", "diff", f"--unified={context_lines}", "--cached", "HEAD"],
                capture_output=True,
                check=True,
                cwd=repo_path,
                text=True,
            )
            staged_diff = result.stdout.strip()
            if staged_diff:
                diff_sections.append("# === STAGED CHANGES ===")
                diff_sections.append(staged_diff)

            # 3. Unstaged changes (working directory vs HEAD)
            result = subprocess.run(
                ["git", "diff", f"--unified={context_lines}", "HEAD"],
                capture_output=True,
                check=True,
                cwd=repo_path,
                text=True,
            )
            unstaged_diff = result.stdout.strip()
            if unstaged_diff:
                diff_sections.append("# === UNSTAGED CHANGES ===")
                diff_sections.append(unstaged_diff)

            # 4. Untracked files (show them as new files)
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True,
                check=True,
                cwd=repo_path,
                text=True,
            )
            untracked_files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
            if untracked_files:
                diff_sections.append("# === UNTRACKED FILES ===")
                for file_path in untracked_files:
                    try:
                        # Show the content of untracked files
                        result = subprocess.run(
                            ["git", "diff", "--no-index", "/dev/null", file_path],
                            capture_output=True,
                            cwd=repo_path,
                            text=True,
                        )
                        if result.stdout.strip():
                            diff_sections.append(result.stdout.strip())
                    except subprocess.CalledProcessError:
                        # If diff fails, just mention the file
                        diff_sections.append(f"# New untracked file: {file_path}")

        # Combine all diff sections
        if not diff_sections:
            scope_desc = "committed, staged, or unstaged" if diff_scope == "all" else "committed"
            raise GitRepositoryError(
                f"No changes found between current branch and '{base_branch}'. "
                f"Make sure you have {scope_desc} changes."
            )

        return "\n\n".join(diff_sections)

    except subprocess.CalledProcessError as e:
        raise GitRepositoryError(f"Failed to generate diff: {e}")


def get_git_info(repo_path: Path, base_branch: str) -> dict:
    """Get comprehensive git repository information."""
    try:
        current_branch = get_current_branch(repo_path)
        merge_base = get_merge_base(repo_path, base_branch)

        # Get current HEAD commit
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, check=True, cwd=repo_path, text=True
        )
        head_commit = result.stdout.strip()

        # Get diff stats
        result = subprocess.run(
            ["git", "diff", "--stat", f"{merge_base}..HEAD"],
            capture_output=True,
            check=True,
            cwd=repo_path,
            text=True,
        )
        diff_stats = result.stdout.strip()

        # Parse stats for structured data
        stats = {"files": 0, "insertions": 0, "deletions": 0}
        if diff_stats:
            lines = diff_stats.split("\n")
            if lines:
                summary_line = lines[-1]
                # Parse line like " 5 files changed, 120 insertions(+), 45 deletions(-)"
                parts = summary_line.split(",")
                for part in parts:
                    part = part.strip()
                    if "file" in part:
                        stats["files"] = int(part.split()[0])
                    elif "insertion" in part:
                        stats["insertions"] = int(part.split()[0])
                    elif "deletion" in part:
                        stats["deletions"] = int(part.split()[0])

        return {
            "current_branch": current_branch,
            "base_branch": base_branch,
            "merge_base": merge_base,
            "head_commit": head_commit,
            "commit_range": f"{merge_base}..{head_commit}",
            "stats": stats,
            "diff_stats": diff_stats,
        }

    except subprocess.CalledProcessError as e:
        raise GitRepositoryError(f"Failed to get git info: {e}")


def validate_and_prepare_repo(repo_path: Path, base_branch: str) -> tuple[dict, str | None]:
    """Validate repository and return git info with any warnings."""
    validate_git_repo(repo_path)
    validate_base_branch(repo_path, base_branch)

    # Check for uncommitted changes (warning, not blocking)
    has_uncommitted, status_message = check_uncommitted_changes(repo_path)
    warning = status_message if has_uncommitted else None

    git_info = get_git_info(repo_path, base_branch)

    return git_info, warning
