# git-reviewer

A Python project called git-reviewer

## Features

- **CLI Application** with Typer framework
- **Rich terminal output** with colors and formatting
- **Interactive commands** with help and configuration
- **Global installation** support via pipx
- **Modern Python tooling** (uv, ruff, black, mypy, pytest)
- **Pre-commit hooks** for code quality
- **GitHub Actions** CI/CD workflows
- **Comprehensive testing** with coverage reports
- **Version management** with automated bumping
- **Professional project structure** following best practices

## Installation

### Development Installation

```bash
# Clone the repository
git clone https://github.com/ryannikolaidis/git-reviewer.git
cd git-reviewer

# Install dependencies
make install-dev
```

### Global Installation
Install git_reviewer globally using pipx (recommended):

```bash
# Build and install globally
make install-package

# Or manually:
make build
pipx install .
```

After installation, you can use the `git-reviewer` command from anywhere.

### Uninstall

```bash
make uninstall-package
# Or: pipx uninstall git_reviewer
```
## Usage

```bash
# Show help
git-reviewer --help

# Say hello
git-reviewer hello
git-reviewer hello --name Alice
git-reviewer hello --name Bob --loud

# Show application info
git-reviewer info

# Manage configuration
git-reviewer config
git-reviewer config --show
```

## Development

### Setup

```bash
# Install development dependencies
make install-dev

# Install pre-commit hooks
uv run pre-commit install
```

### Common Commands

```bash
# Run tests
make test

# Run linting
make lint

# Fix formatting
make tidy

# Run all checks
make check

# Build documentation
make docs

# Build and serve docs locally
make docs-serve

# Build package
make build

# Install globally
make install-package

# Bump version
make version-dev
```

### Testing

```bash
# Run tests with coverage
make test-cov
```

## Documentation

This project uses [Sphinx](https://www.sphinx-doc.org/) for documentation generation.

### Building Documentation

```bash
# Build HTML documentation
make docs

# Build and serve locally (opens in browser at http://localhost:8080)
make docs-serve

# Clean documentation build files
make clean
```

### Editing Documentation

Documentation source files live under `docs/sphinx/`:

- `docs/sphinx/index.rst` - Main documentation page
- `docs/sphinx/installation.rst` - Installation instructions
- `docs/sphinx/usage.rst` - Usage examples and tutorials
- `docs/sphinx/api.rst` - Auto-generated API reference

### GitHub Pages Deployment

Documentation is automatically built and deployed to GitHub Pages when you push to the `main` branch. The docs will be available at:

`https://ryannikolaidis.github.io/git-reviewer/`

To enable GitHub Pages:
1. Go to your repository Settings → Pages
2. Select "GitHub Actions" as the source
3. Push to main branch to trigger the first build


## License

MIT License - see [LICENSE](LICENSE) file for details.
