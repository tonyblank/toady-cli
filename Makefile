.PHONY: help install install-dev test test-fast test-integration test-performance test-analysis lint format format-check type-check pre-commit check check-fast fix-check clean build

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "🚀 Installation:"
	@echo "  make install         Install package in production mode"
	@echo "  make install-dev     Install package in development mode with all dev dependencies"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test            Run all tests with coverage (80% threshold)"
	@echo "  make test-ci         Run tests exactly like CI pipeline (no fail-fast)"
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
	@echo "✅ CI/CD Pipeline:"
	@echo "  make check           🎯 Run COMPREHENSIVE CI/CD pipeline (all checks + tests)"
	@echo "  make check-fast      ⚡ Run FAST quality checks (no tests, quick validation)"
	@echo "  make fix-check       🔧 Run checks with auto-fixing (like CI pipeline)"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean           Remove build artifacts and cache files"
	@echo "  make build           Build distribution packages"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	@echo "🧪 Running comprehensive test suite with 80% coverage requirement..."
	python3 scripts/test_config.py full

test-ci:
	@echo "🔄 Running tests exactly like CI pipeline (no fail-fast, all tests)..."
	pytest tests/ --cov=toady --cov-branch --cov-report=term-missing:skip-covered --cov-report=html:htmlcov --cov-report=xml:coverage.xml --cov-fail-under=80 --durations=10 --tb=short -v --continue-on-collection-errors

test-fast:
	@echo "⚡ Running fast unit tests..."
	python3 scripts/test_config.py fast

test-integration:
	@echo "🔗 Running integration tests..."
	python3 scripts/test_config.py integration

test-performance:
	@echo "📊 Running performance benchmarks..."
	python3 scripts/test_config.py performance

test-analysis:
	@echo "📈 Generating test suite analysis..."
	python3 scripts/test_config.py analyze
	python3 scripts/test_config.py report

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

# 🎯 COMPREHENSIVE CI/CD PIPELINE
# This is the main command that runs all quality checks, tests, and validations
# with beautiful reporting and elegant progress tracking
check:
	@echo "🚀 Launching comprehensive CI/CD pipeline..."
	python3 scripts/ci_check.py full

# ⚡ FAST QUALITY CHECK PIPELINE
# Quick validation without running the full test suite
# Perfect for rapid development feedback
check-fast:
	@echo "⚡ Running fast quality check pipeline..."
	python3 scripts/ci_check.py fast

# 🔧 AUTO-FIXING PIPELINE
# Runs checks with automatic fixing where possible
# This is the legacy behavior for backwards compatibility
fix-check:
	@echo "🔧 Running auto-fixing CI/CD pipeline..."
	@echo ""
	@echo "📋 Step 1: Auto-fixing code issues..."
	pre-commit run --all-files || true
	@echo ""
	@echo "🔍 Step 2: Running type checks..."
	mypy --strict --ignore-missing-imports src
	@echo ""
	@echo "🧪 Step 3: Running comprehensive tests..."
	python3 scripts/test_config.py full
	@echo ""
	@echo "✨ Auto-fixing pipeline completed!"

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
