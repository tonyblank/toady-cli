# Toady CLI Examples and Usage Patterns

This document provides comprehensive examples for using Toady CLI to manage GitHub pull request reviews efficiently. Examples are organized by use case and include both human-friendly and agent-optimized patterns.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Basic Workflow](#basic-workflow)
- [Agent/Automation Patterns](#agent-automation-patterns)
- [Advanced Usage](#advanced-usage)
- [Error Handling](#error-handling)
- [Integration Examples](#integration-examples)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Ensure GitHub CLI is installed and authenticated:
```bash
# Install GitHub CLI (if not already installed)
brew install gh  # macOS
# sudo apt install gh  # Ubuntu
# winget install GitHub.cli  # Windows

# Authenticate with GitHub
gh auth login

# Verify authentication
gh auth status

# Ensure you have repo access
gh repo view owner/repository
```

## Basic Workflow

### 1. Interactive Review Management

```bash
# Start with interactive PR selection
toady fetch

# View in human-readable format
toady fetch --format pretty

# Reply to a comment
toady reply --id "PRRT_kwDOO3WQIc5Rv3_r" --body "Thanks for the feedback! Fixed in latest commit."

# Resolve the thread
toady resolve --thread-id "PRRT_kwDOO3WQIc5Rv3_r"
```

### 2. Targeted PR Review

```bash
# Fetch unresolved threads from specific PR
toady fetch --pr 123

# Include resolved threads for context
toady fetch --pr 123 --resolved

# Reply with verbose context
toady reply --id "IC_kwDOABcD12MAAAABcDE3fg" --body "Updated the implementation" --verbose

# Bulk resolve all threads
toady resolve --all --pr 123
```

## Agent/Automation Patterns

### 1. Structured Data Processing

```bash
# Get all thread IDs for processing
THREAD_IDS=$(toady fetch --pr 123 | jq -r '.[].thread_id')

# Process each thread
echo "$THREAD_IDS" | while read -r thread_id; do
    echo "Processing thread: $thread_id"
    toady reply --id "$thread_id" --body "Automated response: Issue acknowledged"
    toady resolve --thread-id "$thread_id"
done
```

### 2. Conditional Processing

```bash
# Process only threads from specific reviewers
toady fetch --pr 123 | jq -r '.[] | select(.author == "reviewer-username") | .thread_id' | while read -r id; do
    toady reply --id "$id" --body "Thanks for the review!"
done

# Process threads in specific files
toady fetch --pr 123 | jq -r '.[] | select(.file_path | contains("src/")) | .thread_id' | while read -r id; do
    toady reply --id "$id" --body "Code updated as requested"
done
```

### 3. Batch Operations with Error Handling

```bash
#!/bin/bash
# batch_review_response.sh

PR_NUMBER=${1:-123}
RESPONSE_MESSAGE=${2:-"Thank you for the review! Addressed in latest commit."}

echo "Processing PR #$PR_NUMBER..."

# Fetch threads and process with error handling
toady fetch --pr "$PR_NUMBER" | jq -r '.[] | select(.is_resolved == false) | .thread_id' | while read -r thread_id; do
    echo "Processing thread: $thread_id"
    
    # Reply with error handling
    if toady reply --id "$thread_id" --body "$RESPONSE_MESSAGE"; then
        echo "  ✅ Reply posted successfully"
        
        # Resolve with error handling
        if toady resolve --thread-id "$thread_id"; then
            echo "  ✅ Thread resolved successfully"
        else
            echo "  ❌ Failed to resolve thread: $thread_id"
        fi
    else
        echo "  ❌ Failed to reply to thread: $thread_id"
    fi
done

echo "Batch processing complete."
```

### 4. Integration with CI/CD

```yaml
# .github/workflows/auto-review-response.yml
name: Auto Review Response
on:
  pull_request_review:
    types: [submitted]

jobs:
  respond:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup GitHub CLI
        run: |
          gh auth login --with-token <<< "${{ secrets.GITHUB_TOKEN }}"
      
      - name: Install Toady
        run: pip install toady-cli
      
      - name: Process Review Comments
        run: |
          # Auto-acknowledge review comments
          toady fetch --pr ${{ github.event.pull_request.number }} | \
          jq -r '.[] | select(.is_resolved == false) | .thread_id' | \
          head -5 | \
          while read -r id; do
            toady reply --id "$id" --body "Thank you for the review! I'll address this shortly."
          done
```

## Advanced Usage

### 1. Complex Filtering and Processing

```bash
# Find and respond to urgent threads (containing specific keywords)
toady fetch --pr 123 | jq -r '.[] | select(.body | test("urgent|critical|security"; "i")) | .thread_id' | while read -r id; do
    toady reply --id "$id" --body "🚨 Urgent issue acknowledged. Working on fix immediately."
done

# Process threads by file type
toady fetch --pr 123 | jq -r '.[] | select(.file_path | endswith(".py")) | .thread_id' | while read -r id; do
    toady reply --id "$id" --body "Python code review feedback received and will be addressed."
done

# Batch resolve with confirmation bypass
toady resolve --all --pr 123 --yes --limit 50
```

### 2. Monitoring and Reporting

```bash
#!/bin/bash
# review_status_report.sh

PR_NUMBER=$1
if [[ -z "$PR_NUMBER" ]]; then
    echo "Usage: $0 <pr_number>"
    exit 1
fi

echo "📊 Review Status Report for PR #$PR_NUMBER"
echo "========================================="

# Get thread data
THREADS=$(toady fetch --pr "$PR_NUMBER" --resolved)

# Count statistics
TOTAL=$(echo "$THREADS" | jq length)
UNRESOLVED=$(echo "$THREADS" | jq '[.[] | select(.is_resolved == false)] | length')
RESOLVED=$(echo "$THREADS" | jq '[.[] | select(.is_resolved == true)] | length')

echo "Total threads: $TOTAL"
echo "Unresolved: $UNRESOLVED"
echo "Resolved: $RESOLVED"

if [[ $UNRESOLVED -gt 0 ]]; then
    echo
    echo "📋 Unresolved Threads:"
    echo "$THREADS" | jq -r '.[] | select(.is_resolved == false) | "- \(.thread_id): \(.body[0:80])..."'
fi
```

### 3. Custom Response Templates

```bash
#!/bin/bash
# smart_reviewer_response.sh

THREAD_ID=$1
THREAD_CONTENT=$(toady fetch --pr 123 | jq -r ".[] | select(.thread_id == \"$THREAD_ID\") | .body")

# Generate contextual responses based on content
if echo "$THREAD_CONTENT" | grep -qi "test"; then
    RESPONSE="Great point about testing! I'll add comprehensive tests for this functionality."
elif echo "$THREAD_CONTENT" | grep -qi "performance"; then
    RESPONSE="Thanks for the performance feedback. I'll optimize this section and add benchmarks."
elif echo "$THREAD_CONTENT" | grep -qi "security"; then
    RESPONSE="Security concern noted. I'll review this implementation and ensure it follows best practices."
else
    RESPONSE="Thank you for the feedback! I'll address this in the next commit."
fi

toady reply --id "$THREAD_ID" --body "$RESPONSE"
toady resolve --thread-id "$THREAD_ID"
```

## Error Handling

### 1. Robust Error Handling Script

```bash
#!/bin/bash
# robust_review_handler.sh

set -euo pipefail

PR_NUMBER=${1:-}
if [[ -z "$PR_NUMBER" ]]; then
    echo "Error: PR number required"
    echo "Usage: $0 <pr_number>"
    exit 1
fi

# Function to handle API errors
handle_error() {
    local command=$1
    local error_output=$2
    
    if echo "$error_output" | grep -q "authentication_failed"; then
        echo "❌ Authentication failed. Run: gh auth login"
        exit 1
    elif echo "$error_output" | grep -q "rate_limit_exceeded"; then
        echo "⏱️ Rate limit exceeded. Waiting 60 seconds..."
        sleep 60
        return 1  # Retry
    elif echo "$error_output" | grep -q "pr_not_found"; then
        echo "❌ PR #$PR_NUMBER not found or no access"
        exit 1
    else
        echo "❌ Unknown error in $command: $error_output"
        return 1
    fi
}

# Fetch with retry logic
fetch_with_retry() {
    local max_attempts=3
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        echo "Attempt $attempt: Fetching threads..."
        
        local output
        if output=$(toady fetch --pr "$PR_NUMBER" 2>&1); then
            echo "$output"
            return 0
        else
            if ! handle_error "fetch" "$output"; then
                ((attempt++))
                if [[ $attempt -le $max_attempts ]]; then
                    echo "Retrying in 5 seconds..."
                    sleep 5
                fi
            else
                exit 1
            fi
        fi
    done
    
    echo "❌ Failed to fetch after $max_attempts attempts"
    exit 1
}

# Main execution
echo "🚀 Starting robust review processing for PR #$PR_NUMBER"
THREADS=$(fetch_with_retry)

echo "$THREADS" | jq -r '.[] | select(.is_resolved == false) | .thread_id' | while read -r thread_id; do
    echo "Processing thread: $thread_id"
    
    # Reply with error handling
    if ! toady reply --id "$thread_id" --body "Acknowledged and working on this feedback."; then
        echo "  ⚠️ Failed to reply to $thread_id, continuing..."
        continue
    fi
    
    # Resolve with error handling
    if ! toady resolve --thread-id "$thread_id"; then
        echo "  ⚠️ Failed to resolve $thread_id, continuing..."
        continue
    fi
    
    echo "  ✅ Successfully processed $thread_id"
done

echo "✨ Review processing completed"
```

## Integration Examples

### 1. Integration with Jira

```bash
#!/bin/bash
# jira_integration.sh

PR_NUMBER=$1
JIRA_TICKET=${2:-}

# Extract Jira ticket from PR title if not provided
if [[ -z "$JIRA_TICKET" ]]; then
    JIRA_TICKET=$(gh pr view "$PR_NUMBER" --json title -q '.title' | grep -oE '[A-Z]+-[0-9]+' | head -1)
fi

if [[ -n "$JIRA_TICKET" ]]; then
    JIRA_LINK="https://yourcompany.atlassian.net/browse/$JIRA_TICKET"
    RESPONSE="Thanks for the review! This addresses $JIRA_TICKET: $JIRA_LINK"
else
    RESPONSE="Thanks for the review! Addressed in latest commit."
fi

# Process threads with Jira context
toady fetch --pr "$PR_NUMBER" | jq -r '.[] | select(.is_resolved == false) | .thread_id' | while read -r id; do
    toady reply --id "$id" --body "$RESPONSE"
done
```

### 2. Integration with Slack

```bash
#!/bin/bash
# slack_integration.sh

PR_NUMBER=$1
SLACK_WEBHOOK=${SLACK_WEBHOOK:-"https://hooks.slack.com/services/YOUR/WEBHOOK/URL"}

# Get review statistics
STATS=$(toady fetch --pr "$PR_NUMBER" --resolved | jq '{
    total: length,
    unresolved: [.[] | select(.is_resolved == false)] | length,
    resolved: [.[] | select(.is_resolved == true)] | length
}')

TOTAL=$(echo "$STATS" | jq -r '.total')
UNRESOLVED=$(echo "$STATS" | jq -r '.unresolved')
RESOLVED=$(echo "$STATS" | jq -r '.resolved')

# Send Slack notification
curl -X POST -H 'Content-type: application/json' \
    --data "{
        \"text\": \"📊 Review Status for PR #$PR_NUMBER\",
        \"attachments\": [{
            \"color\": \"$([[ $UNRESOLVED -eq 0 ]] && echo \"good\" || echo \"warning\")\",
            \"fields\": [
                {\"title\": \"Total Threads\", \"value\": \"$TOTAL\", \"short\": true},
                {\"title\": \"Unresolved\", \"value\": \"$UNRESOLVED\", \"short\": true},
                {\"title\": \"Resolved\", \"value\": \"$RESOLVED\", \"short\": true}
            ]
        }]
    }" \
    "$SLACK_WEBHOOK"
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Authentication Problems

```bash
# Check GitHub CLI authentication
gh auth status

# Re-authenticate if needed
gh auth login --scopes repo

# Verify repository access
gh repo view owner/repository
```

#### 2. Thread ID Issues

```bash
# Get correct thread IDs
toady fetch --pr 123 | jq -r '.[] | "Thread ID: \(.thread_id), Comment ID: \(.comment_id)"'

# Use --help-ids for detailed ID guidance
toady reply --help-ids
```

#### 3. Rate Limiting

```bash
# Check rate limit status
gh api rate_limit

# Use smaller batch sizes
toady fetch --pr 123 --limit 20

# Add delays between operations
for id in $(toady fetch --pr 123 | jq -r '.[].thread_id'); do
    toady reply --id "$id" --body "Response"
    sleep 2  # Add delay
done
```

#### 4. Debugging Commands

```bash
# Enable debug mode
export TOADY_DEBUG=1
toady fetch --pr 123

# Check detailed error information
toady --debug fetch --pr 123

# Validate specific thread ID
toady reply --id "PRRT_kwDOO3WQIc5Rv3_r" --body "test" --format pretty
```

### Best Practices

1. **Always use thread IDs from `toady fetch` output** for maximum compatibility
2. **Test commands with `--format pretty`** before automating
3. **Use `--limit`** to control API usage in large PRs
4. **Implement retry logic** for production automation
5. **Handle authentication errors gracefully** in CI/CD
6. **Use meaningful reply messages** that add value to the review process
7. **Monitor API rate limits** when processing multiple PRs

### Performance Tips

- Use `--limit` to reduce API calls for large PRs
- Cache `toady fetch` results when processing multiple operations
- Process threads in parallel for large-scale operations (with rate limit consideration)
- Use `--yes` flag for bulk operations in automation

For more help:
- `toady --help` - Main help
- `toady <command> --help` - Command-specific help  
- `toady reply --help-ids` - Detailed ID type documentation

## Contributing

Found a useful pattern not covered here? Please contribute by:
1. Adding your example to this file
2. Testing it thoroughly
3. Submitting a pull request

---

*This document is part of the Toady CLI project. For the latest version and additional resources, visit the [GitHub repository](https://github.com/your-org/toady-cli).*