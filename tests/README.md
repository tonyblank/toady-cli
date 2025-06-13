# Test Framework Documentation

This document describes the comprehensive test framework setup for the Toady CLI project.

## Test Organization

The test suite is organized into the following structure:

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (isolated, fast)
│   ├── formatters/          # Output formatting tests
│   ├── models/              # Data model tests
│   ├── parsers/             # Data parsing tests
│   ├── services/            # Business logic tests
│   └── validators/          # Input validation tests
├── integration/             # Integration tests
│   ├── cli/                 # CLI command integration tests
│   └── test_*.py           # End-to-end integration tests
└── test_*.py               # General tests and examples
```

## Test Markers

The framework uses pytest markers to organize and filter tests:

### Primary Categories
- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Integration tests with external dependencies
- `@pytest.mark.slow` - Tests that take longer than 1 second

### Functional Categories
- `@pytest.mark.cli` - Command-line interface tests
- `@pytest.mark.service` - Service layer tests
- `@pytest.mark.model` - Data model and structure tests
- `@pytest.mark.formatter` - Output formatting tests
- `@pytest.mark.parser` - Data parsing tests
- `@pytest.mark.validator` - Input validation tests

### Special Categories
- `@pytest.mark.mock` - Tests that heavily use mocking
- `@pytest.mark.real_api` - Tests that make actual API calls
- `@pytest.mark.parametrized` - Parametrized tests with multiple scenarios
- `@pytest.mark.smoke` - Basic smoke tests for critical functionality
- `@pytest.mark.regression` - Regression tests for specific bug fixes

## Running Tests

### All Tests
```bash
pytest
```

### By Category
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Formatter tests only
pytest -m formatter

# Exclude slow tests
pytest -m "not slow"

# CLI tests only
pytest -m cli

# Service layer tests
pytest -m service
```

### Coverage Reports
```bash
# Terminal coverage report
pytest --cov=toady

# HTML coverage report
pytest --cov=toady --cov-report=html

# Coverage with missing lines
pytest --cov=toady --cov-report=term-missing
```

## Test Configuration

### pytest.ini
- Comprehensive marker definitions
- Coverage configuration
- Test discovery patterns
- Performance settings

### pyproject.toml
- Additional pytest configuration
- Development dependencies
- Tool configuration for pytest plugins

### conftest.py
- Shared fixtures for common test data
- Mock service configurations
- Test data generators
- Performance baselines

## Fixtures

### Session-scoped Fixtures
- `sample_datetime` - Consistent datetime for tests
- `sample_comment` - Reusable Comment instance
- `sample_review_thread` - Reusable ReviewThread instance
- `performance_baseline` - Performance expectations

### Function-scoped Fixtures
- `runner` - Click CLI test runner
- `mock_gh_command` - GitHub CLI command mock
- `comment_factory` - Dynamic Comment creation
- `thread_factory` - Dynamic ReviewThread creation
- `test_data_generator` - Bulk test data generation

### Service Mocks
- `mock_github_service` - GitHub API service mock
- `mock_fetch_service` - Fetch service mock
- `mock_reply_service` - Reply service mock
- `mock_resolve_service` - Resolve service mock

## Best Practices

### Test Organization
1. Use appropriate markers for all test classes
2. Group related tests in classes
3. Use descriptive test and class names
4. Keep tests focused and atomic

### Performance
1. Use session-scoped fixtures for expensive setup
2. Mock external dependencies
3. Mark slow tests appropriately
4. Use test data generators for bulk data

### Coverage
1. Aim for >80% code coverage
2. Focus on critical business logic
3. Test error conditions and edge cases
4. Exclude appropriate files from coverage

### Mocking
1. Mock external services and APIs
2. Use realistic mock data
3. Test both success and failure scenarios
4. Verify mock interactions when appropriate

## CI/CD Integration

The test framework is integrated with:
- Pre-commit hooks for quality checks
- GitHub Actions for automated testing
- Coverage reporting and thresholds
- Code quality tools (black, ruff, mypy)

## Example Usage

```python
import pytest
from toady.models.models import ReviewThread

@pytest.mark.model
@pytest.mark.unit
class TestReviewThread:
    """Test the ReviewThread model."""

    def test_creation(self, thread_factory):
        """Test thread creation."""
        thread = thread_factory(status="RESOLVED")
        assert thread.status == "RESOLVED"

    @pytest.mark.parametrize("status", ["RESOLVED", "UNRESOLVED"])
    def test_status_values(self, thread_factory, status):
        """Test different status values."""
        thread = thread_factory(status=status)
        assert thread.status == status
```

This framework provides a solid foundation for comprehensive testing that supports both development and CI/CD workflows.
