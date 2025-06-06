# Toady CLI 🐸

[![CI](https://github.com/yourusername/toady-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/toady-cli/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/yourusername/toady-cli/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/toady-cli)
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
git clone https://github.com/yourusername/toady-cli.git
cd toady-cli
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/yourusername/toady-cli.git
cd toady-cli
make install-dev
```

## 🎯 Quick Start

### Fetch Unresolved Review Threads

```bash
# Get unresolved threads as JSON (default)
toady fetch --pr 123

# Get human-readable output
toady fetch --pr 123 --pretty
```

### Reply to a Review Comment

```bash
toady reply --comment-id 12345678 --body "Thanks for the feedback! Fixed in latest commit."
```

### Resolve/Unresolve Review Threads

```bash
# Resolve a thread
toady resolve --thread-id abc123def

# Unresolve a thread
toady resolve --thread-id abc123def --undo
```

## 🛠️ Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/toady-cli.git
cd toady-cli

# Install in development mode with all dependencies
make install-dev
```

### Running Tests

```bash
# Run all tests with coverage
make test

# Run specific test file
pytest tests/test_cli.py
```

### Code Quality Checks

```bash
# Run ALL checks (recommended before committing)
make check

# Individual checks
make lint        # Run ruff linting
make format      # Format with black
make type-check  # Type check with mypy
```

### Pre-commit Hooks

Pre-commit hooks are automatically installed with `make install-dev`. They run on every commit to ensure code quality.

## 🧪 Testing

The project uses pytest for testing with comprehensive coverage tracking:

```bash
# Run tests with coverage report
make test

# Generate HTML coverage report
pytest --cov=toady --cov-report=html
open htmlcov/index.html
```

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

For more detailed documentation, visit our [GitHub Wiki](https://github.com/yourusername/toady-cli/wiki).

## 🐛 Bug Reports

Found a bug? Please [open an issue](https://github.com/yourusername/toady-cli/issues/new) with a clear description and steps to reproduce.