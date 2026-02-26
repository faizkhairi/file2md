# Contributing to file2md

Thanks for your interest in contributing!

## Development Setup

```bash
# Clone the repo
git clone https://github.com/faizkhairi/file2md.git
cd file2md

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install with all dependencies
pip install -e ".[all]"
```

## Running Tests

```bash
pytest
```

## Linting

```bash
ruff check src/ tests/
ruff format src/ tests/  # auto-format
```

## Making Changes

1. Fork the repo and create a branch from `main`
2. Write your code with type hints
3. Add tests for new functionality
4. Run `ruff check` and `pytest` before submitting
5. Open a pull request with a clear description

## Code Style

- Python 3.11+ with type hints
- Ruff for linting and formatting
- Keep functions focused and well-documented
- Follow existing patterns in the codebase

## Reporting Issues

Open an issue at https://github.com/faizkhairi/file2md/issues with:
- Steps to reproduce
- Expected vs actual behavior
- Sample file (if applicable and non-sensitive)
