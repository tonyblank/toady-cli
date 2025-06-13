# Command Unit Tests

This directory contains unit tests for command modules, focusing on testing the core command logic without testing the CLI interface directly.

## Structure

- `__init__.py` - Module initialization
- `test_fetch.py` - Comprehensive unit tests for the fetch command

## Test Coverage

### test_fetch.py

Comprehensive unit tests for the fetch command (`src/toady/commands/fetch.py`) with 95.71% coverage including:

#### Test Classes:

1. **TestFetchCommandCore** - Basic command structure tests
   - Command existence and definition
   - Parameter configuration
   - Default values

2. **TestFetchCommandValidation** - Parameter validation tests
   - PR number validation (called/not called scenarios)
   - Limit validation
   - Error handling for invalid inputs

3. **TestFetchCommandFormatResolution** - Format option handling
   - Pretty flag resolution
   - Format parameter resolution
   - Combined parameter scenarios

4. **TestFetchCommandServiceIntegration** - Service layer integration
   - FetchService instantiation with correct format
   - Service method calls with correct parameters
   - Interactive PR selection scenarios

5. **TestFetchCommandThreadTypeDescription** - Thread type logic
   - Unresolved threads description
   - All threads description (with --resolved flag)

6. **TestFetchCommandOutputFormatting** - Output formatting tests
   - format_threads_output function calls
   - Parameter passing to formatting functions
   - Interactive vs explicit PR scenarios

7. **TestFetchCommandExitConditions** - Exit behavior tests
   - Clean exit on cancelled PR selection
   - Normal completion on successful operations

8. **TestFetchCommandErrorHandling** - Comprehensive error handling
   - Click Exit exception re-raising
   - Pretty format error messages
   - JSON format error responses
   - All exception types (Auth, Timeout, Rate Limit, Service, API, Unexpected)

9. **TestFetchCommandParameterCombinations** - Parameter interaction tests
   - All parameters specified together
   - Minimal parameter usage
   - Interactive selection with options

10. **TestFetchCommandBoundaryConditions** - Edge case testing
    - Maximum/minimum limit values
    - Empty and large result sets
    - Boundary value testing

11. **TestFetchCommandMockingPatterns** - Test infrastructure validation
    - Service mock patterns
    - Format resolution mocking
    - Click context usage

## Test Patterns

### Mocking Strategy
- Uses `@patch` decorators to mock dependencies
- Mocks `FetchService`, `resolve_format_from_options`, and `format_threads_output`
- Uses CLI runner approach via `runner.invoke(cli, ["fetch", ...])` for realistic testing

### Fixture Usage
- Leverages existing `runner` fixture from conftest.py
- Uses module-scoped fixtures for performance
- Follows established patterns in the codebase

### Coverage Goals
- Achieves 95.71% coverage on the fetch command module
- Tests all major code paths and error conditions
- Focuses on unit testing without integration dependencies

## Usage

Run the fetch command tests:
```bash
pytest tests/unit/commands/test_fetch.py -v
```

Run with coverage:
```bash
pytest tests/unit/commands/test_fetch.py --cov=src/toady/commands/fetch --cov-report=term-missing
```
