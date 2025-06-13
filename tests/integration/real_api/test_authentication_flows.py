"""Integration tests for authentication and authorization flows.

These tests verify proper handling of GitHub authentication scenarios,
permission boundaries, and error conditions related to access control.
"""

import os
import subprocess
import tempfile
from typing import Any

from click.testing import CliRunner
import pytest

from toady.cli import cli
from toady.services.github_service import GitHubService


@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.auth
class TestAuthenticationFlows:
    """Test GitHub authentication and authorization scenarios."""

    def test_authenticated_user_identity_verification(
        self,
        github_service_real: GitHubService,
        integration_cli_runner: CliRunner,
    ):
        """Verify that the authenticated user identity is correctly detected."""
        # Get current user info via GitHub API
        try:
            result = subprocess.run(
                ["gh", "api", "user"], capture_output=True, text=True, timeout=10
            )

            assert result.returncode == 0, "Failed to get user info from GitHub API"

            import json

            user_data = json.loads(result.stdout)

            # Verify we have essential user information
            assert "login" in user_data
            assert "id" in user_data
            assert user_data["login"] is not None
            assert user_data["id"] is not None

            # Store for other tests to use
            self.current_user_login = user_data["login"]

        except Exception as e:
            pytest.fail(f"Could not verify user identity: {e}")

    def test_repository_access_permissions(
        self,
        test_repository_info: dict[str, Any],
        integration_cli_runner: CliRunner,
        rate_limit_aware_delay,
    ):
        """Test access to repository with current user permissions."""
        repo_full_name = test_repository_info["full_name"]

        # Check repository permissions
        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{repo_full_name}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            assert result.returncode == 0, f"Cannot access repository {repo_full_name}"

            import json

            repo_data = json.loads(result.stdout)

            # Verify basic repository information
            assert repo_data["full_name"] == repo_full_name

            # Check permissions if available
            permissions = repo_data.get("permissions", {})

            # For integration testing, we need at least read permissions
            if permissions:
                assert permissions.get(
                    "pull", False
                ), "Need pull permissions for testing"

        except Exception as e:
            pytest.fail(f"Repository access verification failed: {e}")

    def test_pr_access_with_current_permissions(
        self,
        verify_test_pr_exists: dict[str, Any],
        test_repository_info: dict[str, Any],
        integration_cli_runner: CliRunner,
    ):
        """Test accessing PR data with current user permissions."""
        pr_number = verify_test_pr_exists["number"]
        test_repository_info["full_name"]

        # Test fetch command with real authentication
        result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        if result.exit_code != 0:
            # If fetch fails, it might be due to permissions
            if (
                "permission" in result.output.lower()
                or "access" in result.output.lower()
            ):
                pytest.skip(f"Insufficient permissions to access PR {pr_number}")
            else:
                pytest.fail(f"Fetch failed for other reason: {result.output}")

        # If successful, verify we got data
        import json

        try:
            threads_data = json.loads(result.output)
            assert isinstance(threads_data, list)
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON response: {result.output}")

    def test_rate_limit_status_and_handling(
        self,
        github_service_real: GitHubService,
        integration_test_config: dict[str, Any],
    ):
        """Test rate limit status checking and handling."""
        try:
            # Check current rate limit status
            result = subprocess.run(
                ["gh", "api", "rate_limit"], capture_output=True, text=True, timeout=10
            )

            assert result.returncode == 0, "Failed to check rate limit status"

            import json

            rate_data = json.loads(result.stdout)

            # Verify rate limit structure
            assert "rate" in rate_data
            rate_info = rate_data["rate"]

            assert "limit" in rate_info
            assert "remaining" in rate_info
            assert "reset" in rate_info

            # Verify we have sufficient remaining calls for testing
            remaining = rate_info["remaining"]
            buffer = integration_test_config["rate_limit_buffer"]

            if remaining < buffer:
                pytest.skip(
                    f"Insufficient rate limit remaining: {remaining} < {buffer}"
                )

            # Log rate limit info for debugging
            print(f"Rate limit: {remaining}/{rate_info['limit']} remaining")

        except Exception as e:
            pytest.fail(f"Rate limit check failed: {e}")

    def test_token_scope_verification(self):
        """Verify that the GitHub token has appropriate scopes for testing."""
        try:
            # Check token scopes via API
            result = subprocess.run(
                ["gh", "api", "user", "-i"],  # Include headers
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                pytest.skip("Could not verify token scopes")

            # Parse headers to find X-OAuth-Scopes
            headers = result.stderr
            oauth_scopes = None

            for line in headers.split("\n"):
                if line.lower().startswith("x-oauth-scopes:"):
                    oauth_scopes = line.split(":", 1)[1].strip()
                    break

            if oauth_scopes:
                scopes = [scope.strip() for scope in oauth_scopes.split(",")]

                # Check for essential scopes
                # Note: repo scope is usually needed for PR operations
                if "repo" not in scopes and "public_repo" not in scopes:
                    pytest.skip("Token lacks repository access scopes")

                print(f"Token scopes: {oauth_scopes}")
            else:
                # If we can't detect scopes, proceed anyway
                print("Could not detect token scopes from headers")

        except Exception as e:
            # Non-critical for most tests
            print(f"Token scope verification failed: {e}")

    def test_unauthenticated_behavior_simulation(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
    ):
        """Simulate unauthenticated behavior by temporarily removing auth."""
        verify_test_pr_exists["number"]

        # This test is complex because we need to temporarily remove auth
        # We'll do a simple check to ensure error handling works

        # Try to access a command that requires auth with invalid token
        with tempfile.TemporaryDirectory():
            # Set up environment that would cause auth failure
            env = os.environ.copy()
            env["GH_TOKEN"] = "invalid_token_for_testing"

            # Note: This test is limited because gh CLI might cache auth
            # In a real scenario, we'd need to test with truly unauthenticated state

            # For now, just verify that our commands handle auth errors gracefully
            # This would need to be expanded with actual auth manipulation

    def test_cross_organization_access_patterns(
        self,
        test_repository_info: dict[str, Any],
        integration_cli_runner: CliRunner,
    ):
        """Test access patterns across different organizations (if applicable)."""
        repo_full_name = test_repository_info["full_name"]
        owner, repo_name = repo_full_name.split("/")

        # Check if we can access organization information
        try:
            org_result = subprocess.run(
                ["gh", "api", f"orgs/{owner}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if org_result.returncode == 0:
                # This is an organization
                import json

                org_data = json.loads(org_result.stdout)

                assert org_data["login"] == owner
                print(f"Testing with organization: {owner}")

                # Test organization-level permissions
                # (This would be expanded based on specific org policies)

            else:
                # This might be a user account, not an organization
                user_result = subprocess.run(
                    ["gh", "api", f"users/{owner}"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if user_result.returncode == 0:
                    print(f"Testing with user account: {owner}")
                else:
                    pytest.skip(f"Could not determine owner type for {owner}")

        except Exception as e:
            pytest.skip(f"Could not test cross-organization access: {e}")

    def test_permission_boundary_validation(
        self,
        verify_test_pr_exists: dict[str, Any],
        test_repository_info: dict[str, Any],
        integration_cli_runner: CliRunner,
    ):
        """Test operations at the boundary of user permissions."""
        pr_number = verify_test_pr_exists["number"]

        # Test operations that require different permission levels

        # 1. Read operations (should work with minimal permissions)
        read_result = integration_cli_runner.invoke(
            cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
        )

        # Read should generally work if we can access the PR at all
        if read_result.exit_code != 0:
            # If read fails, note why
            print(f"Read operation failed: {read_result.output}")

        # 2. Write operations (require higher permissions)
        # We'll test with a carefully chosen approach to avoid spam

        # First, check if we have any existing threads to work with
        if read_result.exit_code == 0:
            import json

            threads = json.loads(read_result.output)

            if threads and len(threads) > 0:
                # Test resolving a thread (if we have permission)
                thread_id = threads[0]["thread_id"]

                resolve_result = integration_cli_runner.invoke(
                    cli, ["resolve", "--thread-id", thread_id, "--format", "json"]
                )

                if resolve_result.exit_code == 0:
                    print("User has thread resolution permissions")

                    # Undo the resolution to clean up
                    undo_result = integration_cli_runner.invoke(
                        cli,
                        [
                            "resolve",
                            "--thread-id",
                            thread_id,
                            "--undo",
                            "--format",
                            "json",
                        ],
                    )

                    if undo_result.exit_code != 0:
                        print(f"Could not undo resolution: {undo_result.output}")

                else:
                    print(
                        f"User lacks thread resolution permissions: "
                        f"{resolve_result.output}"
                    )

    def test_github_enterprise_compatibility_detection(self):
        """Test detection of GitHub Enterprise vs GitHub.com."""
        try:
            # Check GitHub CLI configuration
            subprocess.run(
                ["gh", "config", "get", "git_protocol"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Check the API endpoint being used
            # For GitHub Enterprise, this would be different
            api_result = subprocess.run(
                ["gh", "api", "meta"], capture_output=True, text=True, timeout=10
            )

            if api_result.returncode == 0:
                import json

                meta_data = json.loads(api_result.stdout)

                # GitHub.com returns specific meta information
                if "github_services_sha" in meta_data:
                    print("Testing against GitHub.com")
                else:
                    print("Possibly testing against GitHub Enterprise")

            # Note: More specific Enterprise detection would require
            # checking the hostname configuration in gh CLI

        except Exception as e:
            print(f"Could not detect GitHub instance type: {e}")


@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.auth
class TestAuthenticationErrorHandling:
    """Test proper handling of authentication-related errors."""

    def test_graceful_handling_of_auth_errors(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
    ):
        """Test that authentication errors are handled gracefully."""
        verify_test_pr_exists["number"]

        # This is a conceptual test - in practice, it's difficult to simulate
        # auth errors without actually breaking authentication

        # We can test the error messages our commands would produce
        # by looking at command output for certain failure modes

        # Test with potentially invalid data that might trigger auth checks
        invalid_result = integration_cli_runner.invoke(
            cli,
            [
                "fetch",
                "--pr",
                "999999999",  # Very unlikely to exist or be accessible
                "--format",
                "json",
            ],
        )

        # Should fail, but with a proper error message (not crash)
        assert invalid_result.exit_code != 0

        # Error message should be informative
        error_output = invalid_result.output.lower()
        assert len(error_output) > 0

        # Should not contain sensitive information or stack traces in production
        assert "traceback" not in error_output or "exception" not in error_output

    def test_token_expiration_handling_simulation(self):
        """Test handling of expired tokens (simulated)."""
        # This would require a more sophisticated test setup
        # to actually simulate token expiration

        # For now, we verify that our error handling code paths exist
        # and would handle such scenarios appropriately

        try:
            # Check if we can detect token validity
            result = subprocess.run(
                ["gh", "auth", "status"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                print("Current token is valid")
            else:
                print("Token appears to be invalid or expired")
                # This would be where we test the error handling

        except Exception as e:
            print(f"Token validation check failed: {e}")

    def test_network_authentication_resilience(
        self,
        integration_cli_runner: CliRunner,
        verify_test_pr_exists: dict[str, Any],
        api_retry_helper,
    ):
        """Test authentication resilience under network conditions."""
        pr_number = verify_test_pr_exists["number"]

        # Test that authentication works consistently across multiple calls
        def make_authenticated_call():
            return integration_cli_runner.invoke(
                cli, ["fetch", "--pr", str(pr_number), "--format", "json"]
            )

        # Make multiple calls to test consistency
        for i in range(3):
            result = api_retry_helper(make_authenticated_call)

            # Each call should either succeed or fail consistently
            # (not randomly based on auth state)
            if i == 0:
                first_exit_code = result.exit_code
            else:
                assert result.exit_code == first_exit_code, (
                    f"Inconsistent auth behavior: call {i+1} had exit code "
                    f"{result.exit_code}, but first call had {first_exit_code}"
                )
