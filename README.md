# Toady CLI 🐸

[![CI](https://github.com/tonyblank/toady-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/tonyblank/toady-cli/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/tonyblank/toady-cli/branch/main/graph/badge.svg)](https://codecov.io/gh/tonyblank/toady-cli)
[![PyPI version](https://badge.fury.io/py/toady-cli.svg)](https://badge.fury.io/py/toady-cli)
[![Python versions](https://img.shields.io/pypi/pyversions/toady-cli.svg)](https://pypi.org/project/toady-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A modern CLI tool for efficiently managing GitHub pull request code reviews. Toady helps you fetch unresolved review comments, post replies, and manage review thread resolution—all from your command line.

## ✨ Features

- 🔍 **Fetch unresolved review threads** from any GitHub pull request
- 💬 **Reply to review comments** directly from your terminal
- ✅ **Resolve/unresolve review threads** with simple commands
- 🎨 **Pretty output formatting** for human readability
- 🤖 **JSON output** for automation and scripting
- 🔐 **Secure authentication** via GitHub CLI (`gh`)
- 🏗️ **Modular architecture** with clean separation of concerns
- 🧪 **Comprehensive testing** with 80% coverage requirement
- ⚡ **Fast CI/CD pipeline** with elegant reporting
- 🛡️ **GraphQL schema validation** for API compatibility

## 📋 Prerequisites

- Python 3.8 or higher
- [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated

## 🚀 Installation

### From PyPI (Recommended)

```bash
pip install toady-cli
```

### From Source

```bash
git clone https://github.com/tonyblank/toady-cli.git
cd toady-cli
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/tonyblank/toady-cli.git
cd toady-cli
make install-dev
```

## 🎯 Quick Start

### Fetch Unresolved Review Threads

```bash
# Auto-detect PR (recommended)
toady fetch

# Get unresolved threads from specific PR
toady fetch --pr 123

# Get human-readable output
toady fetch --format pretty

# Include resolved threads
toady fetch --resolved
```

### Reply to a Review Comment

```bash
# Reply to a review thread (recommended)
toady reply --id PRRT_kwDOO3WQIc5Rv3_r --body "Thanks for the feedback! Fixed in latest commit."

# Reply using numeric ID (legacy)
toady reply --id 12345678 --body "Fixed!"

# Get help with ID types
toady reply --help-ids
```

### Resolve/Unresolve Review Threads

```bash
# Resolve a thread
toady resolve --thread-id abc123def

# Unresolve a thread
toady resolve --thread-id abc123def --undo

# Resolve all unresolved threads at once
toady resolve --all --pr 123
```

### Smart PR Detection

```bash
# Toady automatically detects your PR context:
# - Single PR: fetches automatically
# - Multiple PRs: shows interactive selection
# - No PRs: displays helpful message
toady fetch

# Override auto-detection for specific PR
toady fetch --pr 123
```

### Schema Validation

```bash
# Validate all GraphQL queries against GitHub's schema
toady schema validate

# Validate a specific GraphQL query
toady schema check "query { ... }"

# Fetch and cache GitHub's GraphQL schema
toady schema fetch
```

## 🛠️ Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/tonyblank/toady-cli.git
cd toady-cli

# Install in development mode with all dependencies
make install-dev
```

### 🏗️ Architecture

Toady CLI follows a modular architecture with clear separation of concerns:

```
src/toady/
├── cli.py                    # Main CLI entry point and command registration
├── command_utils.py          # CLI command utilities and helpers
├── error_handling.py         # Error handling and exception management
├── exceptions.py             # Custom exception hierarchy
├── utils.py                  # General utilities
├── commands/                 # Modular command implementations
│   ├── fetch.py             # Fetch command logic
│   ├── reply.py             # Reply command logic
│   ├── resolve.py           # Resolve command logic
│   └── schema.py            # Schema validation commands
├── services/                 # Business logic services
│   ├── github_service.py    # Core GitHub API interactions
│   ├── fetch_service.py     # Fetch-specific business logic
│   ├── reply_service.py     # Reply-specific business logic
│   ├── resolve_service.py   # Resolution-specific business logic
│   ├── pr_selection.py      # PR selection logic
│   └── pr_selector.py       # PR selector utilities
├── formatters/              # Output formatting modules
│   ├── formatters.py        # Main formatter logic
│   ├── format_interfaces.py # Formatter interfaces and base classes
│   ├── format_selection.py  # Format selection utilities
│   ├── json_formatter.py    # JSON-specific formatting
│   └── pretty_formatter.py  # Pretty output formatting
├── models/                  # Data models
│   └── models.py           # Data models for GitHub entities
├── parsers/                 # Data parsing modules
│   ├── graphql_parser.py   # GraphQL query parsing
│   ├── graphql_queries.py  # GraphQL query definitions
│   └── parsers.py          # Data parsing utilities
└── validators/              # Validation modules
    ├── node_id_validation.py # GitHub node ID validation
    ├── schema_validator.py   # GraphQL schema validation
    └── validation.py         # General validation utilities
```

### 🧪 Testing

The project uses pytest with a comprehensive test suite organized by type:

```bash
# 🎯 Run comprehensive CI/CD pipeline (recommended)
make check

# 🚀 Testing options:
make test                    # All tests with 80% coverage requirement
make test-fast              # Fast unit tests only
make test-integration       # Integration tests only
make test-performance       # Performance benchmarks
make test-analysis          # Generate detailed test suite analysis

# 🔍 Code Quality:
make check-fast             # Quick validation (no tests)
make lint                   # Run ruff linting
make format                 # Format with black
make type-check            # Type check with mypy
make pre-commit            # Run all pre-commit hooks
```

#### Test Organization

```
tests/
├── unit/                    # Fast, isolated unit tests
│   ├── services/           # Service layer tests
│   ├── formatters/         # Output formatting tests
│   ├── models/             # Data model tests
│   └── validators/         # Validation logic tests
├── integration/            # Integration tests
│   ├── cli/               # CLI command tests using CliRunner
│   └── ...                # GitHub API integration tests
└── conftest.py            # Shared fixtures and test configuration
```

#### Test Categories

Tests are organized with pytest markers for targeted execution:

- `unit`: Fast, isolated tests with no external dependencies
- `integration`: Tests requiring GitHub CLI or external services
- `slow`: Performance tests and benchmarks
- `cli`: Command-line interface integration tests
- `service`: Service layer business logic tests

### 🎯 Quality Assurance

The project maintains high code quality through:

- **Coverage Requirement**: 80% test coverage minimum
- **Code Formatting**: Black for consistent code style
- **Linting**: Ruff for fast and comprehensive code analysis
- **Type Checking**: MyPy with strict configuration
- **Pre-commit Hooks**: Automatic code quality checks on every commit
- **CI/CD Pipeline**: Comprehensive checks with fail-fast behavior

#### CI/CD Pipeline

The `make check` command runs a comprehensive pipeline:

1. **Environment Validation**: Verify all tools are available
2. **Code Formatting**: Check Black formatting compliance
3. **Linting**: Run Ruff analysis for code quality
4. **Type Checking**: Validate type hints with MyPy
5. **Test Suite**: Execute all 610+ tests with coverage tracking

The pipeline provides elegant, colorized output with detailed timing and failure reporting.

## 📦 Building and Publishing

```bash
# Build distribution packages
make build

# Upload to PyPI (requires credentials)
twine upload dist/*
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests and checks (`make check`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for elegant CLI interactions
- Styled with [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- Integrates with [GitHub CLI](https://cli.github.com/) for secure API access

## 📚 Documentation

For more detailed documentation, visit our [GitHub Wiki](https://github.com/tonyblank/toady-cli/wiki).

## 🛠️ Troubleshooting

### Authentication Issues

- **Run:** `gh auth login`
- **Verify:** `gh auth status`
- **Ensure repo scope:** `gh auth login --scopes repo`

### Common Errors

- **"authentication_required":** GitHub CLI not logged in
- **"pr_not_found":** PR doesn't exist or no repository access
- **"rate_limit_exceeded":** Too many API calls, wait and retry
- **"thread_not_found":** Invalid thread ID or thread was deleted

### Debug Mode

- **Set TOADY_DEBUG=1** or use `--debug` flag for detailed error info
- **Use `--format pretty`** for human-readable output during testing

### ID Issues

- **Always use thread IDs** from `toady fetch` output
- **Use `toady reply --help-ids`** for complete ID documentation
- **Thread IDs** (PRRT_, PRT_, RT_) are more reliable than comment IDs

### Rate Limiting

- **Use `--limit` option** to reduce API calls
- **Add delays** between operations in scripts
- **Check limits:** `gh api rate_limit`

## 🐛 Bug Reports

Found a bug? Please [open an issue](https://github.com/tonyblank/toady-cli/issues/new) with a clear description and steps to reproduce.
