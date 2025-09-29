"""Command-line interface for git-reviewer."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import create_default_config, get_models_config, load_config
from .context import build_repo_context, get_context_summary, resolve_context_paths
from .errors import (
    GitRepositoryError,
    GitReviewerError,
)
from .git_integration import generate_diff, validate_and_prepare_repo
from .nllm_runner import NLLMRunner
from .template import format_prompt_for_nllm, populate_template

app = typer.Typer(
    name="git-reviewer",
    help="AI-powered code review tool using multiple LLM models",
    add_completion=False,
)
console = Console()


@app.command()
def review(
    repo_path: str | None = typer.Argument(
        None, help="Path to git repository (default: current directory)"
    ),
    config_path: str | None = typer.Option(None, "--config", help="Path to configuration file"),
    models: list[str] = typer.Option(
        [], "--model", help="Model name to use (can be specified multiple times)"
    ),
    output_dir: str | None = typer.Option(
        None, "--output-dir", help="Directory for review outputs"
    ),
    context_files: list[str] = typer.Option(
        [], "--context-file", help="Context files to include (multiple allowed)"
    ),
    context_lines: int | None = typer.Option(
        None, "--context-lines", help="Number of context lines in git diff"
    ),
    base_branch: str | None = typer.Option(None, "--base-branch", help="Base branch for diff"),
    timeout: int | None = typer.Option(None, "--timeout", help="Timeout per model in seconds"),
    retries: int | None = typer.Option(None, "--retries", help="Number of retries per model"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Review git changes using AI models."""

    try:
        # Determine repository path
        if repo_path:
            repo_path_obj = Path(repo_path).resolve()
        else:
            repo_path_obj = Path.cwd()

        console.print(f"[dim]Reviewing repository: {repo_path_obj}[/dim]")

        # Load configuration
        config_override = {}
        if context_lines is not None:
            config_override.setdefault("git", {})["context_lines"] = context_lines
        if base_branch is not None:
            config_override.setdefault("git", {})["base_branch"] = base_branch
        if timeout is not None:
            config_override.setdefault("defaults", {})["timeout"] = timeout
        if retries is not None:
            config_override.setdefault("defaults", {})["retries"] = retries

        config = load_config(cwd=repo_path_obj, config_override=config_override)

        # Use specified models or all configured models
        model_names = models if models else None
        model_configs = get_models_config(config, model_names)
        if not model_configs:
            console.print("[red]No models configured. Please check your configuration.[/red]")
            raise typer.Exit(1)

        if verbose:
            console.print(
                f"[dim]Using {len(model_configs)} models: {', '.join(m['name'] for m in model_configs)}[/dim]"
            )

        # Validate and prepare repository
        git_config = config["git"]
        git_info, warning = validate_and_prepare_repo(repo_path_obj, git_config["base_branch"])

        if warning and verbose:
            console.print(f"[yellow]Warning: {warning}[/yellow]")

        # Generate diff
        diff_content = generate_diff(
            repo_path_obj, git_config["base_branch"], git_config["context_lines"]
        )

        if verbose:
            console.print(f"[dim]Generated diff with {len(diff_content.splitlines())} lines[/dim]")

        # Process context files
        context_file_paths = resolve_context_paths(context_files, repo_path_obj)
        repo_context = build_repo_context(context_file_paths, repo_path_obj)

        if context_file_paths and verbose:
            summary = get_context_summary(context_file_paths)
            console.print(
                f"[dim]Context: {summary['readable_files']} files ({summary['total_size_mb']}MB)[/dim]"
            )

        # Load and populate template
        template_path = Path(config["paths"]["template"])
        if not template_path.is_absolute():
            # Try relative to package
            import git_reviewer

            package_dir = Path(git_reviewer.__file__).parent
            template_path = package_dir / template_path

        populated_template = populate_template(template_path, repo_context, diff_content)
        prompt = format_prompt_for_nllm(populated_template)

        if verbose:
            console.print(f"[dim]Generated prompt with {len(prompt)} characters[/dim]")

        # Prepare output directory for nllm
        if output_dir:
            nllm_output_dir = Path(output_dir)
        else:
            # Check config for output directory (nllm-style), fallback to current directory
            config_output_dir = config["defaults"].get("outdir")
            if config_output_dir:
                nllm_output_dir = Path(config_output_dir).expanduser()
            else:
                nllm_output_dir = Path.cwd() / "git-reviewer-results"

        runner = NLLMRunner(config)

        # Check if nllm is available
        nllm_available, nllm_info = runner.check_nllm_available()
        if not nllm_available:
            console.print(f"[red]nllm not available: {nllm_info}[/red]")
            raise typer.Exit(1)

        if verbose:
            console.print(f"[dim]nllm version: {nllm_info}[/dim]")

        console.print(f"[blue]Running review with {len(model_configs)} models...[/blue]")

        # Execute review (always in parallel)
        execution_result = runner.run_review(model_configs, prompt, nllm_output_dir, parallel=True)

        # Display results
        display_results(execution_result, verbose)

        # Show where results are actually saved (from nllm)
        actual_output_dir = execution_result.get("output_dir", nllm_output_dir)
        console.print(f"\n[cyan]📁 Full results saved to: [bold]{actual_output_dir}[/bold][/cyan]")

        # Exit with appropriate code
        if execution_result["success_count"] == 0:
            console.print("[red]All models failed. See errors above.[/red]")
            raise typer.Exit(1)
        elif execution_result["error_count"] > 0:
            console.print(
                f"[yellow]Completed with {execution_result['error_count']} model failures.[/yellow]"
            )
            raise typer.Exit(2)
        else:
            console.print("[green]Review completed successfully![/green]")

    except GitReviewerError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Review cancelled by user.[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(1)


@app.command()
def init_config() -> None:
    """Initialize a default configuration file."""
    from .config import get_global_config_path

    global_config_path = get_global_config_path()

    if global_config_path.exists():
        console.print(f"[yellow]Configuration already exists at: {global_config_path}[/yellow]")
        overwrite = typer.confirm("Do you want to overwrite it?")
        if not overwrite:
            console.print("Configuration initialization cancelled.")
            return

    # Create directory if it doesn't exist
    global_config_path.parent.mkdir(parents=True, exist_ok=True)

    # Create default configuration
    default_config = create_default_config()

    import yaml

    with open(global_config_path, "w") as f:
        yaml.dump(default_config, f, default_flow_style=False, indent=2)

    console.print(f"[green]Configuration initialized at: {global_config_path}[/green]")
    console.print("[dim]Edit this file to configure your models and preferences.[/dim]")


@app.command()
def check() -> None:
    """Check configuration and dependencies."""

    console.print("[blue]Checking git-reviewer configuration...[/blue]")

    # Check configuration
    try:
        config = load_config()
        console.print("[green]✓[/green] Configuration loaded successfully")

        models = config.get("models", [])
        if models:
            console.print(f"[green]✓[/green] Found {len(models)} configured models")
            if console.is_terminal:
                table = Table(title="Configured Models")
                table.add_column("Model", style="cyan")
                table.add_column("Options", style="dim")

                for model in models:
                    options = " ".join(model.get("options", []))
                    table.add_row(model["name"], options or "[none]")

                console.print(table)
        else:
            console.print("[yellow]⚠[/yellow] No models configured")

    except Exception as e:
        console.print(f"[red]✗[/red] Configuration error: {e}")
        return

    # Check nllm
    runner = NLLMRunner(config)
    nllm_available, nllm_info = runner.check_nllm_available()

    if nllm_available:
        console.print(f"[green]✓[/green] nllm available: {nllm_info}")
    else:
        console.print(f"[red]✗[/red] nllm not available: {nllm_info}")
        return

    # Check git in current directory
    try:
        from .git_integration import validate_git_repo

        validate_git_repo(Path.cwd())
        console.print("[green]✓[/green] Current directory is a valid git repository")
    except GitRepositoryError as e:
        console.print(f"[yellow]⚠[/yellow] Current directory: {e}")

    console.print("\n[green]git-reviewer is ready to use![/green]")


def display_results(execution_result: dict, verbose: bool = False) -> None:
    """Display review execution results."""

    results = execution_result["results"]
    errors = execution_result["errors"]

    if results:
        console.print(f"\n[green]✓ {len(results)} models completed successfully:[/green]")

        for model_name, result in results.items():
            console.print(f"\n[bold cyan]{model_name}:[/bold cyan]")

            # Prefer parsed JSON from nllm if available, fallback to raw output
            if "parsed_output" in result:
                # nllm already parsed the JSON
                import json
                output = json.dumps(result["parsed_output"], indent=2)
            else:
                output = result.get("output", "")
                if output:
                    # Try to pretty-print JSON manually
                    import json
                    try:
                        parsed = json.loads(output)
                        output = json.dumps(parsed, indent=2)
                    except json.JSONDecodeError:
                        pass  # Keep as string

            if output:
                # Truncate very long output unless verbose
                if not verbose and len(output) > 1000:
                    output = output[:1000] + "\n... (truncated, use --verbose for full output)"

                console.print(Panel(output, border_style="green"))
            else:
                console.print("[dim]No output[/dim]")

    if errors:
        console.print(f"\n[red]✗ {len(errors)} models failed:[/red]")

        for model_name, error_info in errors.items():
            console.print(f"\n[bold red]{model_name}:[/bold red]")
            error_msg = error_info.get("error", "Unknown error")
            console.print(f"[red]{error_msg}[/red]")

            if verbose:
                cmd = error_info.get("command", "unknown")
                console.print(f"[dim]Command: {cmd}[/dim]")

                if error_info.get("output"):
                    console.print(f"[dim]Output: {error_info['output']}[/dim]")


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
