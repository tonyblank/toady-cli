.PHONY: help install install-dev test lint format format-check type-check pre-commit check check-strict clean build

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      Install package in production mode"
	@echo "  make install-dev  Install package in development mode with all dev dependencies"
	@echo "  make test         Run all tests with coverage"
	@echo "  make lint         Run linting (ruff)"
	@echo "  make format       Format code with black"
	@echo "  make format-check Check code formatting with black"
	@echo "  make type-check   Run type checking with mypy"
	@echo "  make pre-commit   Run all pre-commit hooks"
	@echo "  make check        Run ALL checks (auto-fixes formatting, like CI pipeline)"
	@echo "  make check-strict Run ALL checks without auto-fixing (strict validation)"
	@echo "  make clean        Remove build artifacts and cache files"
	@echo "  make build        Build distribution packages"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest -v

lint:
	ruff check --no-fix src tests

format:
	black src tests

format-check:
	black --check src tests

type-check:
	mypy --strict --ignore-missing-imports src

pre-commit:
	pre-commit run --all-files

# Main target for running all checks (like CI pipeline)
# This runs pre-commit which automatically fixes formatting, then runs tests
check:
	@echo "🔧 Running pre-commit hooks (auto-fixing issues)..."
	pre-commit run --all-files || true
	@echo "🔍 Running type checks..."
	mypy --strict --ignore-missing-imports src
	@echo "🧪 Running tests..."
	pytest -v

# Strict checking without auto-fixing (fails if formatting needed)
check-strict: format-check lint type-check test
	@echo "✅ All strict checks passed!"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build
