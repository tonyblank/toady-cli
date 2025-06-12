# Real API Integration Tests

This directory contains comprehensive integration tests that interact with actual GitHub APIs to verify end-to-end functionality of the toady CLI.

## Overview

These tests are designed to be **world-class integration tests** that provide confidence in real-world usage scenarios. They cover:

- **End-to-end workflows**: Complete user journeys from fetch to reply to resolve
- **Authentication flows**: GitHub authentication and authorization patterns
- **Network resilience**: Rate limiting, timeouts, retry logic, and error recovery
- **Performance monitoring**: Benchmarking, scalability, and resource utilization

## Test Categories

### 1. End-to-End Workflows (`test_end_to_end_workflows.py`)
- Complete review cycle testing (fetch → reply → resolve)
- Bulk operations testing
- Error recovery workflows
- Interactive command testing
- Format consistency validation

### 2. Authentication Flows (`test_authentication_flows.py`)
- User identity verification
- Repository access permissions
- Rate limit status monitoring
- Token scope validation
- Cross-organization access patterns
- Permission boundary testing

### 3. Network Resilience (`test_network_resilience.py`)
- API timeout handling
- Network retry behavior
- Large response processing
- Concurrent usage patterns
- Progressive backoff testing
- Connection recovery after failures
- Rate limit compliance and error handling

### 4. Performance Monitoring (`test_performance_monitoring.py`)
- Performance baseline establishment
- Memory usage pattern analysis
- Large PR performance testing
- Concurrent operation impact
- Cache effectiveness measurement
- Network latency impact assessment
- Scalability pattern validation
- Resource utilization monitoring

## Environment Setup

### Prerequisites

1. **GitHub CLI Authentication**:
   ```bash
   gh auth login
   gh auth status  # Verify authentication
   ```

2. **Test Repository Access**:
   Set up environment variables for test repository:
   ```bash
   export TOADY_TEST_REPO="your-org/test-repo"
   export TOADY_TEST_PR_NUMBER="1"
   ```

3. **Optional Configuration**:
   ```bash
   export TOADY_API_TIMEOUT="30"
   export TOADY_RATE_LIMIT_BUFFER="100"
   export TOADY_SKIP_SLOW_TESTS="false"
   export TOADY_MAX_RETRY_ATTEMPTS="3"
   export TOADY_RETRY_DELAY="1.0"
   ```

### Test Repository Requirements

The test repository should have:
- At least one pull request with review comments
- Appropriate permissions for the authenticated user
- Active review threads (both resolved and unresolved)

## Running the Tests

### Run All Real API Tests
```bash
pytest tests/integration/real_api/ -m real_api
```

### Run by Category
```bash
# End-to-end workflows only
pytest tests/integration/real_api/test_end_to_end_workflows.py

# Authentication tests only
pytest tests/integration/real_api/test_authentication_flows.py -m auth

# Network resilience tests only
pytest tests/integration/real_api/test_network_resilience.py -m resilience

# Performance tests only
pytest tests/integration/real_api/test_performance_monitoring.py -m performance
```

### Run with Specific Markers
```bash
# Fast tests only (exclude slow tests)
pytest tests/integration/real_api/ -m "real_api and not slow"

# Slow tests only
pytest tests/integration/real_api/ -m "slow"

# Authentication-related tests
pytest tests/integration/real_api/ -m "auth"

# Resilience and error handling tests
pytest tests/integration/real_api/ -m "resilience"

# Performance and scalability tests
pytest tests/integration/real_api/ -m "performance"
```

### Verbose Output with Performance Monitoring
```bash
pytest tests/integration/real_api/ -m real_api -v -s --tb=short
```

## Test Configuration

### Available Pytest Markers

- `@pytest.mark.real_api`: Tests that make actual GitHub API calls
- `@pytest.mark.slow`: Tests that take significant time to complete
- `@pytest.mark.auth`: Authentication and authorization tests
- `@pytest.mark.resilience`: Network resilience and error recovery tests
- `@pytest.mark.performance`: Performance and scalability tests

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TOADY_TEST_REPO` | `toady-test/integration-testing` | GitHub repository for testing |
| `TOADY_TEST_PR_NUMBER` | `1` | PR number to use for testing |
| `TOADY_API_TIMEOUT` | `30` | API call timeout in seconds |
| `TOADY_RATE_LIMIT_BUFFER` | `100` | Minimum rate limit remaining for tests |
| `TOADY_SKIP_SLOW_TESTS` | `false` | Skip slow-running tests |
| `TOADY_MAX_RETRY_ATTEMPTS` | `3` | Maximum retry attempts for failed API calls |
| `TOADY_RETRY_DELAY` | `1.0` | Base delay between retry attempts |

## Test Features

### Smart Test Skipping
Tests automatically skip when:
- GitHub CLI is not authenticated
- Test repository is not accessible
- Rate limits are too low
- Required test data is not available

### Performance Monitoring
Tests include built-in performance monitoring:
- Operation timing and benchmarking
- Memory usage tracking
- Rate limit awareness
- Resource utilization monitoring

### Error Recovery
Tests validate error recovery patterns:
- Transient error handling
- Rate limit compliance
- Network timeout recovery
- Authentication error handling

### Data Consistency
Tests ensure data consistency:
- Multiple fetch operations return consistent results
- State changes persist across operations
- Cache behavior is correct

## CI/CD Integration

### Running in Continuous Integration

For CI environments, use:
```bash
# Skip slow tests in CI
pytest tests/integration/real_api/ -m "real_api and not slow" --maxfail=5

# Or skip real API tests entirely if no auth available
pytest tests/integration/ -m "not real_api"
```

### GitHub Actions Example
```yaml
- name: Run Integration Tests
  env:
    TOADY_TEST_REPO: ${{ secrets.TEST_REPO }}
    TOADY_SKIP_SLOW_TESTS: "true"
  run: |
    gh auth login --with-token <<< "${{ secrets.GITHUB_TOKEN }}"
    pytest tests/integration/real_api/ -m "real_api and not slow"
```

## Debugging and Troubleshooting

### Common Issues

1. **Authentication Errors**:
   ```bash
   gh auth status
   gh auth refresh
   ```

2. **Rate Limit Issues**:
   ```bash
   gh api rate_limit
   # Wait for rate limit reset or increase TOADY_RATE_LIMIT_BUFFER
   ```

3. **Test Repository Access**:
   ```bash
   gh api repos/$TOADY_TEST_REPO
   gh pr list --repo $TOADY_TEST_REPO
   ```

4. **Slow Test Performance**:
   ```bash
   export TOADY_SKIP_SLOW_TESTS=true
   pytest tests/integration/real_api/ -m "not slow"
   ```

### Verbose Debugging
```bash
pytest tests/integration/real_api/ -v -s --tb=long --capture=no
```

### Performance Analysis
```bash
pytest tests/integration/real_api/ -m performance --durations=0
```

## Best Practices

### For Test Development

1. **Always use rate limiting aware delays**
2. **Include proper cleanup for any data created**
3. **Handle authentication and permission errors gracefully**
4. **Include performance assertions where appropriate**
5. **Use descriptive test names and documentation**

### For Test Execution

1. **Check authentication before running tests**
2. **Verify test repository access**
3. **Monitor rate limit usage**
4. **Run slow tests separately when needed**
5. **Use appropriate environment configuration**

## Contributing

When adding new integration tests:

1. Follow the existing patterns and structure
2. Use appropriate pytest markers
3. Include proper error handling and cleanup
4. Add performance monitoring where relevant
5. Update this README if adding new categories
6. Ensure tests work with the provided test fixtures

## Test Quality Metrics

These integration tests aim to achieve:
- **Comprehensive coverage** of real-world usage scenarios
- **Robust error handling** for all failure modes
- **Performance validation** for acceptable response times
- **Reliability testing** under various network conditions
- **Security verification** of authentication flows

The tests serve as both validation and documentation of the system's behavior under real conditions.
