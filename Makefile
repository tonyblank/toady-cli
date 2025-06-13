.PHONY: help install install-dev test test-fast test-integration test-performance test-analysis
.PHONY: lint format format-check type-check pre-commit check check-fast fix-check clean build
.PHONY: sync lock update add remove deps-check shell run

# Single source of truth: ALL commands use uv
export PATH := $(HOME)/.local/bin:$(PATH)

# Default target
help:
	@echo "🐍 Toady CLI Development Commands (Powered by uv)"
	@echo ""
	@echo "🚀 Installation:"
	@echo "  make install         Install package in production mode"
	@echo "  make install-dev     Install package in development mode with all dev dependencies"
	@echo "  make sync            Sync dependencies from lock file (fastest)"
	@echo ""
	@echo "🧪 Testing (Advanced Test Suite):"
	@echo "  make test            Run all tests with coverage (90% threshold)"
	@echo "  make test-fast       Run fast unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-performance Run performance benchmarks"
	@echo "  make test-analysis   Generate test suite analysis report"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  make lint            Run linting (ruff)"
	@echo "  make format          Format code with black"
	@echo "  make format-check    Check code formatting with black"
	@echo "  make type-check      Run type checking with mypy"
	@echo "  make pre-commit      Run all pre-commit hooks"
	@echo ""
	@echo "✅ CI/CD Pipeline (Elegant Reporting):"
	@echo "  make check           🎯 Run COMPREHENSIVE CI/CD pipeline (all checks + tests)"
	@echo "  make check-fast      ⚡ Run FAST quality checks (no tests, quick validation)"
	@echo "  make fix-check       🔧 Run checks with auto-fixing (like CI pipeline)"
	@echo ""
	@echo "📦 Dependency Management:"
	@echo "  make lock            Generate/update lock file with exact versions"
	@echo "  make update          Update dependencies to latest compatible versions"
	@echo "  make add PKG=name    Add new dependency"
	@echo "  make remove PKG=name Remove dependency"
	@echo "  make deps-check      Check for dependency conflicts"
	@echo ""
	@echo "🛠️  Development Utilities:"
	@echo "  make shell           Open shell with project dependencies loaded"
	@echo "  make run ARGS='...'  Run toady CLI in development mode"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean           Remove build artifacts and cache files"
	@echo "  make build           Build distribution packages"

install:
	@echo "📦 Installing package in production mode..."
	uv pip install .

install-dev:
	@echo "🔧 Installing development environment..."
	uv sync --all-extras
	uv run pre-commit install
	@echo "✅ Development environment ready!"

## Testing (Advanced Test Suite - ALL using uv)
test:
	@echo "🧪 Running comprehensive test suite with 90% coverage requirement..."
	uv run python scripts/test_config.py full

test-fast:
	@echo "⚡ Running fast unit tests..."
	uv run python scripts/test_config.py fast

test-integration:
	@echo "🔗 Running integration tests..."
	uv run python scripts/test_config.py integration

test-performance:
	@echo "📊 Running performance benchmarks..."
	uv run python scripts/test_config.py performance

test-analysis:
	@echo "📈 Generating test suite analysis..."
	uv run python scripts/test_config.py analyze
	uv run python scripts/test_config.py report

## Code Quality (ALL using uv)
lint:
	uv run ruff check --no-fix src tests

format:
	uv run black src tests

format-check:
	uv run black --check src tests

type-check:
	uv run mypy --strict --ignore-missing-imports src

pre-commit:
	uv run pre-commit run --all-files

## CI/CD Pipeline (Elegant Reporting - ALL using uv)
# 🎯 COMPREHENSIVE CI/CD PIPELINE
# This is the main command that runs all quality checks, tests, and validations
# with beautiful reporting and elegant progress tracking
check:
	@echo "🚀 Launching comprehensive CI/CD pipeline..."
	uv run python scripts/ci_check.py full

# ⚡ FAST QUALITY CHECK PIPELINE
# Quick validation without running the full test suite
# Perfect for rapid development feedback
check-fast:
	@echo "⚡ Running fast quality check pipeline..."
	uv run python scripts/ci_check.py fast

# 🔧 AUTO-FIXING PIPELINE
# Runs checks with automatic fixing where possible
# This is the legacy behavior for backwards compatibility
fix-check:
	@echo "🔧 Running auto-fixing CI/CD pipeline..."
	@echo ""
	@echo "📋 Step 1: Auto-fixing code issues..."
	uv run pre-commit run --all-files || true
	@echo ""
	@echo "🔍 Step 2: Running type checks..."
	uv run mypy --strict --ignore-missing-imports src
	@echo ""
	@echo "🧪 Step 3: Running comprehensive tests..."
	uv run python scripts/test_config.py full
	@echo ""
	@echo "✨ Auto-fixing pipeline completed!"

## Dependency Management (uv native commands)
sync:
	@echo "⚡ Syncing dependencies from lock file..."
	uv sync

lock:
	@echo "🔒 Generating lock file with exact versions..."
	uv lock

update:
	@echo "⬆️  Updating dependencies to latest compatible versions..."
	uv lock --upgrade

add:
	@echo "➕ Adding dependency: $(PKG)"
	uv add $(PKG)

remove:
	@echo "➖ Removing dependency: $(PKG)"
	uv remove $(PKG)

deps-check:
	@echo "🔍 Checking for dependency conflicts..."
	uv pip check

## Development Utilities (uv powered)
shell:
	@echo "🐚 Opening shell with project dependencies..."
	uv shell

run:
	@echo "🚀 Running toady CLI in development mode..."
	uv run toady $(ARGS)

## Maintenance (Enhanced)
clean:
	@echo "🧹 Cleaning build artifacts and cache..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf test-reports/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	@echo "📦 Building distribution packages..."
	uv build
