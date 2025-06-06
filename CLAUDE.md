# Toady CLI - Development Guide

## Project Overview
Toady is a Python CLI tool for managing GitHub PR code reviews efficiently. It integrates with GitHub CLI (`gh`) to fetch unresolved comments, post replies, and manage review thread resolution status.

## Core Commands
1. `toady fetch --pr <PR_NUMBER>` - Fetch unresolved review threads
2. `toady reply --comment-id <COMMENT_ID> --body "message"` - Reply to comments
3. `toady resolve --thread-id <THREAD_ID> [--undo]` - Manage thread resolution

## Development Approach

### Test-Driven Development (TDD)
1. **Write tests first** for each feature before implementation
2. **Mock GitHub API calls** using pytest fixtures
3. **Test edge cases**: authentication failures, rate limits, invalid inputs
4. **Integration tests** with actual `gh` CLI (marked for CI/CD)

### Project Structure
```
toady-cli/
├── toady/
│   ├── __init__.py
│   ├── cli.py          # Click CLI interface
│   ├── github.py       # GitHub API interactions via gh
│   ├── formatters.py   # JSON/pretty output formatting
│   └── utils.py        # Helper functions
├── tests/
│   ├── test_cli.py
│   ├── test_github.py
│   ├── test_formatters.py
│   └── fixtures/       # Mock data for tests
├── setup.py
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

### Implementation Guidelines

#### 1. GitHub Integration
- Use `subprocess` to call `gh` CLI commands
- Parse JSON output from `gh api` calls
- Handle authentication via `gh` CLI (no token management)
- Implement proper error handling for API failures

#### 2. CLI Design (using Click)
```python
@click.group()
def cli():
    """Toady - GitHub PR review management tool"""
    pass

@cli.command()
@click.option('--pr', required=True, type=int)
@click.option('--pretty', is_flag=True)
def fetch(pr, pretty):
    """Fetch unresolved review threads"""
    # Implementation
```

#### 3. Error Handling
- Graceful handling of missing `gh` CLI
- Clear error messages for authentication issues
- Rate limit detection and user guidance
- Validation of PR numbers, comment IDs, thread IDs

#### 4. Output Formatting
- Default: JSON for automation/AI tools
- Pretty: Human-readable with colors/formatting
- Consistent structure across commands

### Testing Strategy

#### Unit Tests
- Mock `subprocess` calls to `gh`
- Test each command with various inputs
- Verify output formatting (JSON/pretty)
- Test error scenarios

#### Integration Tests (marked)
```python
@pytest.mark.integration
def test_real_github_api():
    # Tests against actual GitHub API
    # Skip in CI without credentials
```

### Code Quality Standards
- Type hints for all functions
- Docstrings following Google style
- Maximum function length: 20 lines
- DRY principle - extract common patterns
- No hardcoded values - use constants/config

### Development Workflow
1. Check task status: `task-master next`
2. Write failing tests for the feature
3. Implement minimal code to pass tests
4. Refactor for clarity and efficiency
5. Update task: `task-master set-status --id=<id> --status=done`

### Key Dependencies
- Python 3.7+
- Click (CLI framework)
- pytest (testing)
- GitHub CLI (`gh`) - external dependency

### API Patterns

#### GraphQL Query (via gh)
```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $number) {
        reviewThreads(first: 100) {
          nodes {
            id
            isResolved
            comments(first: 10) {
              nodes {
                id
                body
                author { login }
              }
            }
          }
        }
      }
    }
  }
' -f owner=OWNER -f repo=REPO -f number=PR_NUMBER
```

#### REST API (via gh)
```bash
gh api repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies \
  --method POST \
  --field body="Reply text"
```

### Future Considerations
- Batch operations support
- Configuration file (~/.toady/config.yml)
- Plugin system for custom formatters
- Caching for performance
- Webhook integration for real-time updates

### Common Pitfalls to Avoid
- Don't store GitHub tokens - rely on `gh` auth
- Don't assume PR exists - validate first
- Don't ignore rate limits - handle gracefully
- Don't overcomplicate MVP - focus on core features
- Don't forget cross-platform compatibility

### Testing Commands
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=toady

# Run only unit tests (skip integration)
pytest -m "not integration"

# Run specific test file
pytest tests/test_cli.py

# Linting and formatting
black toady/ tests/
flake8 toady/ tests/
mypy toady/
```

### Release Checklist
1. All tests passing
2. Documentation updated
3. Version bumped in setup.py
4. CHANGELOG updated
5. Tagged release in git
6. Published to PyPI

This guide ensures elegant, maintainable, and well-tested development of toady-cli.