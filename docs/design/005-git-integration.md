# Git Integration Design

## Overview

git-reviewer integrates deeply with Git to extract repository context, generate diffs, and validate repository state. The Git integration is designed to be robust, flexible, and handle various repository configurations while providing detailed change analysis.

## Core Git Operations

### Repository Validation

```python
def validate_git_repo(repo_path):
    """Validate that the path contains a valid Git repository."""
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        raise GitRepositoryError(f"Not a git repository: {repo_path}")

    # Additional validation could include:
    # - Checking for corrupted repository
    # - Validating git config
    # - Ensuring HEAD exists
```

### Repository Preparation

```python
def validate_and_prepare_repo(repo_path, base_branch):
    """Validate repository and gather git information."""
    validate_git_repo(repo_path)

    # Get current repository state
    current_branch = get_current_branch(repo_path)
    head_commit = get_head_commit(repo_path)

    # Validate base branch exists
    if not branch_exists(repo_path, base_branch):
        available_branches = get_available_branches(repo_path)
        raise GitRepositoryError(
            f"Base branch '{base_branch}' not found. "
            f"Available branches: {', '.join(available_branches)}"
        )

    # Calculate merge base
    merge_base = get_merge_base(repo_path, base_branch, "HEAD")

    # Generate statistics
    stats = get_diff_stats(repo_path, f"{merge_base}..HEAD")

    git_info = GitInfo(
        current_branch=current_branch,
        base_branch=base_branch,
        merge_base=merge_base,
        head_commit=head_commit,
        commit_range=f"{merge_base}..{head_commit}",
        stats=stats,
        diff_stats=format_diff_stats(stats)
    )

    return git_info, None  # warning placeholder
```

## Diff Generation

### Diff Scopes

git-reviewer supports two diff scopes:

1. **`all`** (default): Includes committed, staged, and unstaged changes
2. **`committed`**: Only includes committed changes

```python
def generate_diff(repo_path, base_branch, context_lines, diff_scope="all"):
    """Generate git diff based on specified scope."""
    if diff_scope == "committed":
        # Only committed changes since base branch
        merge_base = get_merge_base(repo_path, base_branch, "HEAD")
        return get_committed_diff(repo_path, merge_base, context_lines)
    elif diff_scope == "all":
        # All changes: committed + staged + unstaged
        return get_comprehensive_diff(repo_path, base_branch, context_lines)
    else:
        raise ValueError(f"Invalid diff_scope: {diff_scope}. Must be 'all' or 'committed'")
```

### Committed Changes Only

```python
def get_committed_diff(repo_path, merge_base, context_lines):
    """Get diff for committed changes only."""
    cmd = [
        "git", "diff",
        f"--unified={context_lines}",
        "--no-color",
        "--no-ext-diff",
        merge_base + "..HEAD"
    ]

    result = subprocess.run(
        cmd, cwd=repo_path, capture_output=True, text=True, check=True
    )
    return result.stdout
```

### All Changes (Committed + Staged + Unstaged)

```python
def get_comprehensive_diff(repo_path, base_branch, context_lines):
    """Get diff including all changes: committed, staged, and unstaged."""
    merge_base = get_merge_base(repo_path, base_branch, "HEAD")

    # Get committed changes
    committed_diff = get_committed_diff(repo_path, merge_base, context_lines)

    # Get staged changes
    staged_cmd = [
        "git", "diff",
        f"--unified={context_lines}",
        "--no-color", "--cached"
    ]
    staged_result = subprocess.run(
        staged_cmd, cwd=repo_path, capture_output=True, text=True, check=True
    )

    # Get unstaged changes
    unstaged_cmd = [
        "git", "diff",
        f"--unified={context_lines}",
        "--no-color"
    ]
    unstaged_result = subprocess.run(
        unstaged_cmd, cwd=repo_path, capture_output=True, text=True, check=True
    )

    # Combine all diffs with section headers
    combined_parts = []

    if committed_diff.strip():
        combined_parts.append("=== COMMITTED CHANGES ===")
        combined_parts.append(committed_diff)

    if staged_result.stdout.strip():
        combined_parts.append("=== STAGED CHANGES ===")
        combined_parts.append(staged_result.stdout)

    if unstaged_result.stdout.strip():
        combined_parts.append("=== UNSTAGED CHANGES ===")
        combined_parts.append(unstaged_result.stdout)

    return "\n".join(combined_parts)
```

## Git Information Extraction

### Branch Operations

```python
def get_current_branch(repo_path):
    """Get the current branch name."""
    cmd = ["git", "symbolic-ref", "--short", "HEAD"]
    try:
        result = subprocess.run(
            cmd, cwd=repo_path, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Detached HEAD state
        return get_head_commit(repo_path)[:8]  # Short SHA

def get_head_commit(repo_path):
    """Get the current HEAD commit SHA."""
    cmd = ["git", "rev-parse", "HEAD"]
    result = subprocess.run(
        cmd, cwd=repo_path, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()

def branch_exists(repo_path, branch_name):
    """Check if a branch exists locally or remotely."""
    # Check local branches
    cmd = ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"]
    local_result = subprocess.run(cmd, cwd=repo_path, capture_output=True)

    if local_result.returncode == 0:
        return True

    # Check remote branches
    cmd = ["git", "show-ref", "--verify", f"refs/remotes/origin/{branch_name}"]
    remote_result = subprocess.run(cmd, cwd=repo_path, capture_output=True)

    return remote_result.returncode == 0

def get_available_branches(repo_path):
    """Get list of available local and remote branches."""
    cmd = ["git", "branch", "-a", "--format=%(refname:short)"]
    result = subprocess.run(
        cmd, cwd=repo_path, capture_output=True, text=True, check=True
    )
    branches = [
        branch.strip().replace("origin/", "")
        for branch in result.stdout.split("\n")
        if branch.strip() and not branch.startswith("origin/HEAD")
    ]
    return sorted(set(branches))
```

### Merge Base Calculation

```python
def get_merge_base(repo_path, base_branch, target_branch):
    """Find the merge base between two branches."""
    # First try to find remote base branch
    remote_branch = f"origin/{base_branch}"
    cmd = ["git", "merge-base", remote_branch, target_branch]

    try:
        result = subprocess.run(
            cmd, cwd=repo_path, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Fall back to local branch
        cmd = ["git", "merge-base", base_branch, target_branch]
        result = subprocess.run(
            cmd, cwd=repo_path, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
```

## Statistics and Metadata

### Diff Statistics

```python
def get_diff_stats(repo_path, commit_range):
    """Get diff statistics for a commit range."""
    cmd = ["git", "diff", "--stat", "--numstat", commit_range]
    result = subprocess.run(
        cmd, cwd=repo_path, capture_output=True, text=True, check=True
    )

    lines = result.stdout.strip().split("\n")
    if not lines or lines == [""]:
        return {"files": 0, "insertions": 0, "deletions": 0}

    total_insertions = 0
    total_deletions = 0
    file_count = 0

    for line in lines:
        parts = line.split("\t")
        if len(parts) >= 3:  # insertions, deletions, filename
            try:
                insertions = int(parts[0]) if parts[0] != "-" else 0
                deletions = int(parts[1]) if parts[1] != "-" else 0
                total_insertions += insertions
                total_deletions += deletions
                file_count += 1
            except ValueError:
                continue

    return {
        "files": file_count,
        "insertions": total_insertions,
        "deletions": total_deletions
    }

def format_diff_stats(stats):
    """Format diff statistics for display."""
    files = stats["files"]
    insertions = stats["insertions"]
    deletions = stats["deletions"]

    parts = []
    if files:
        parts.append(f"{files} file{'s' if files != 1 else ''} changed")
    if insertions:
        parts.append(f"{insertions} insertion{'s' if insertions != 1 else ''}(+)")
    if deletions:
        parts.append(f"{deletions} deletion{'s' if deletions != 1 else ''}(-)")

    return ", ".join(parts) if parts else "No changes"
```

## Error Handling

### Git Command Execution

```python
def run_git_command(repo_path, cmd, check=True):
    """Execute a git command with proper error handling."""
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown git error"
        raise GitRepositoryError(f"Git command failed: {' '.join(cmd)}\nError: {error_msg}")
    except FileNotFoundError:
        raise GitRepositoryError("Git command not found. Please ensure git is installed and in PATH.")
```

### Repository State Validation

```python
def validate_repository_state(repo_path, base_branch):
    """Validate repository is in a good state for review."""
    warnings = []

    # Check for unresolved merge conflicts
    if has_merge_conflicts(repo_path):
        raise GitRepositoryError("Repository has unresolved merge conflicts")

    # Check if working directory is clean (warning only)
    if has_unstaged_changes(repo_path):
        warnings.append("Working directory has unstaged changes")

    # Check if we're ahead/behind remote
    remote_status = get_remote_status(repo_path, base_branch)
    if remote_status:
        warnings.append(remote_status)

    return warnings

def has_merge_conflicts(repo_path):
    """Check if repository has unresolved merge conflicts."""
    cmd = ["git", "status", "--porcelain"]
    result = run_git_command(repo_path, cmd)

    for line in result.stdout.split("\n"):
        if line.startswith("UU ") or line.startswith("AA "):
            return True
    return False

def has_unstaged_changes(repo_path):
    """Check if repository has unstaged changes."""
    cmd = ["git", "status", "--porcelain"]
    result = run_git_command(repo_path, cmd)
    return bool(result.stdout.strip())
```

## Advanced Git Features

### Handling Different Repository States

```python
def handle_detached_head(repo_path):
    """Handle detached HEAD state gracefully."""
    current_commit = get_head_commit(repo_path)

    # Try to find branch containing this commit
    cmd = ["git", "branch", "--contains", current_commit]
    result = run_git_command(repo_path, cmd, check=False)

    if result.returncode == 0 and result.stdout.strip():
        branches = [
            line.strip().lstrip("* ")
            for line in result.stdout.split("\n")
            if line.strip()
        ]
        return f"detached-head-on-{branches[0] if branches else current_commit[:8]}"

    return f"detached-head-{current_commit[:8]}"
```

### Submodule Handling

```python
def has_submodules(repo_path):
    """Check if repository has submodules."""
    gitmodules_path = repo_path / ".gitmodules"
    return gitmodules_path.exists()

def get_submodule_changes(repo_path, base_branch, context_lines):
    """Get changes in submodules if present."""
    if not has_submodules(repo_path):
        return ""

    cmd = [
        "git", "submodule", "foreach", "--recursive",
        f"git diff --unified={context_lines} {base_branch}..HEAD"
    ]

    result = run_git_command(repo_path, cmd, check=False)
    if result.returncode == 0 and result.stdout.strip():
        return f"\n=== SUBMODULE CHANGES ===\n{result.stdout}"

    return ""
```

### Binary File Handling

```python
def detect_binary_files(diff_content):
    """Detect binary files in diff content."""
    binary_files = []
    lines = diff_content.split("\n")

    current_file = None
    for line in lines:
        if line.startswith("diff --git"):
            # Extract filename
            parts = line.split()
            if len(parts) >= 4:
                current_file = parts[3].lstrip("b/")
        elif line.startswith("Binary files") and current_file:
            binary_files.append(current_file)
            current_file = None

    return binary_files

def filter_binary_content(diff_content):
    """Filter out binary file content while keeping metadata."""
    lines = diff_content.split("\n")
    filtered_lines = []
    in_binary_file = False

    for line in lines:
        if line.startswith("Binary files"):
            filtered_lines.append(line)
            filtered_lines.append("--- Binary file content excluded from review ---")
            in_binary_file = True
        elif line.startswith("diff --git"):
            in_binary_file = False
            filtered_lines.append(line)
        elif not in_binary_file:
            filtered_lines.append(line)

    return "\n".join(filtered_lines)
```

## Performance Optimizations

### Efficient Diff Generation

```python
def get_optimized_diff(repo_path, base_branch, context_lines, max_diff_size=1_000_000):
    """Generate diff with size limitations for performance."""
    # First, check diff size without generating full content
    cmd = ["git", "diff", "--stat", f"{base_branch}..HEAD"]
    result = run_git_command(repo_path, cmd)

    # Parse diff statistics to estimate size
    stats = parse_diff_stats(result.stdout)
    estimated_size = estimate_diff_size(stats)

    if estimated_size > max_diff_size:
        return get_summary_diff(repo_path, base_branch, context_lines)
    else:
        return get_full_diff(repo_path, base_branch, context_lines)

def get_summary_diff(repo_path, base_branch, context_lines):
    """Generate abbreviated diff for large changesets."""
    cmd = [
        "git", "diff",
        f"--unified={context_lines}",
        "--stat",
        "--summary",
        f"{base_branch}..HEAD"
    ]

    result = run_git_command(repo_path, cmd)
    return result.stdout + "\n--- Full diff truncated due to size ---"
```

## Integration with Review Process

### Context Integration

The Git integration works closely with the context processing system:

```python
def enrich_diff_with_context(diff_content, context_files, repo_path):
    """Enrich diff content with additional context."""
    if not context_files:
        return diff_content

    # Add context file information to diff
    context_header = "=== ADDITIONAL CONTEXT FILES ===\n"

    for file_path in context_files:
        try:
            rel_path = Path(file_path).relative_to(repo_path)
            context_header += f"Context file: {rel_path}\n"
        except ValueError:
            context_header += f"Context file: {file_path}\n"

    return context_header + "\n" + diff_content
```

### Template Integration

Git information is integrated into the template system:

```python
def prepare_git_variables(git_info):
    """Prepare git-related template variables."""
    return {
        "current_branch": git_info.current_branch,
        "base_branch": git_info.base_branch,
        "commit_range": git_info.commit_range,
        "diff_stats": git_info.diff_stats,
        "files_changed": git_info.stats["files"],
        "lines_added": git_info.stats["insertions"],
        "lines_removed": git_info.stats["deletions"]
    }
```

## Future Enhancements

### Planned Git Features

1. **Smart Diff Chunking**: Break large diffs into reviewable chunks
2. **Commit Message Analysis**: Include commit messages in review context
3. **Author Information**: Include change authorship information
4. **File History**: Consider file change history for context
5. **Merge Request Integration**: Support for GitLab/GitHub PR metadata

### Performance Improvements

1. **Caching**: Cache git operations for repeated runs
2. **Incremental Updates**: Only process changed files
3. **Parallel Operations**: Parallelize git command execution
4. **Streaming**: Stream large diffs for memory efficiency

The Git integration provides the foundation for comprehensive repository analysis while maintaining flexibility and performance across different repository configurations and sizes.