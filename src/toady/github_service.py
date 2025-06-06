"""GitHub CLI integration service for toady."""

import json
import subprocess
from typing import Any, List, Optional


class GitHubServiceError(Exception):
    """Base exception for GitHub service errors."""

    pass


class GitHubCLINotFoundError(GitHubServiceError):
    """Raised when gh CLI is not found or not installed."""

    pass


class GitHubAuthenticationError(GitHubServiceError):
    """Raised when gh CLI authentication fails."""

    pass


class GitHubAPIError(GitHubServiceError):
    """Raised when GitHub API calls fail."""

    pass


class GitHubService:
    """Service for interacting with GitHub through the gh CLI."""

    def __init__(self) -> None:
        """Initialize the GitHub service."""
        self.gh_command = "gh"

    def check_gh_installation(self) -> bool:
        """Check if gh CLI is installed and accessible.

        Returns:
            True if gh CLI is installed, False otherwise.
        """
        try:
            result = subprocess.run(
                [self.gh_command, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def get_gh_version(self) -> Optional[str]:
        """Get the installed gh CLI version.

        Returns:
            Version string if gh CLI is installed, None otherwise.

        Raises:
            GitHubCLINotFoundError: If gh CLI is not found.
        """
        try:
            result = subprocess.run(
                [self.gh_command, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise GitHubCLINotFoundError(
                    "gh CLI is not installed or not accessible"
                )

            # Parse version from output like "gh version 2.40.1 (2023-12-13)"
            for line in result.stdout.split("\n"):
                if line.startswith("gh version"):
                    return line.split()[2]

            return None
        except FileNotFoundError as e:
            raise GitHubCLINotFoundError(
                "gh CLI is not installed or not accessible"
            ) from e

    def check_authentication(self) -> bool:
        """Check if gh CLI is authenticated with GitHub.

        Returns:
            True if authenticated, False otherwise.
        """
        try:
            result = subprocess.run(
                [self.gh_command, "auth", "status"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def validate_version_compatibility(self, min_version: str = "2.0.0") -> bool:
        """Validate that the installed gh CLI version meets minimum requirements.

        Args:
            min_version: Minimum required version (default: 2.0.0).

        Returns:
            True if version is compatible, False otherwise.

        Raises:
            GitHubCLINotFoundError: If gh CLI is not found.
        """
        current_version = self.get_gh_version()
        if not current_version:
            return False

        # Simple version comparison (assumes semantic versioning)
        current_parts = [int(x) for x in current_version.split(".")]
        min_parts = [int(x) for x in min_version.split(".")]

        # Pad with zeros if needed
        max_len = max(len(current_parts), len(min_parts))
        current_parts.extend([0] * (max_len - len(current_parts)))
        min_parts.extend([0] * (max_len - len(min_parts)))

        return current_parts >= min_parts

    def run_gh_command(self, args: List[str]) -> Any:
        """Run a gh CLI command with error handling.

        Args:
            args: List of command arguments (excluding 'gh').

        Returns:
            CompletedProcess result.

        Raises:
            GitHubCLINotFoundError: If gh CLI is not found.
            GitHubAuthenticationError: If authentication fails.
            GitHubAPIError: If the GitHub API call fails.
        """
        if not self.check_gh_installation():
            raise GitHubCLINotFoundError("gh CLI is not installed or not accessible")

        try:
            result = subprocess.run(
                [self.gh_command] + args,
                capture_output=True,
                text=True,
                check=False,
            )

            # Check for authentication errors
            if result.returncode != 0 and "authentication" in result.stderr.lower():
                raise GitHubAuthenticationError(
                    f"GitHub authentication failed: {result.stderr}"
                )

            # Check for other API errors
            if result.returncode != 0:
                raise GitHubAPIError(f"GitHub API call failed: {result.stderr}")

            return result

        except FileNotFoundError as e:
            raise GitHubCLINotFoundError(
                "gh CLI is not installed or not accessible"
            ) from e

    def get_json_output(self, args: List[str]) -> Any:
        """Run a gh CLI command and parse JSON output.

        Args:
            args: List of command arguments (excluding 'gh').

        Returns:
            Parsed JSON data.

        Raises:
            GitHubCLINotFoundError: If gh CLI is not found.
            GitHubAuthenticationError: If authentication fails.
            GitHubAPIError: If the GitHub API call fails or JSON parsing fails.
        """
        result = self.run_gh_command(args)

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise GitHubAPIError(f"Failed to parse JSON response: {e}") from e

    def get_current_repo(self) -> Optional[str]:
        """Get the current repository name (owner/repo format).

        Returns:
            Repository name in owner/repo format, or None if not in a repo.

        Raises:
            GitHubCLINotFoundError: If gh CLI is not found.
            GitHubAuthenticationError: If authentication fails.
        """
        try:
            result = self.run_gh_command(["repo", "view", "--json", "nameWithOwner"])
            data = json.loads(result.stdout)
            name_with_owner = data.get("nameWithOwner")
            return name_with_owner if isinstance(name_with_owner, str) else None
        except (GitHubAPIError, json.JSONDecodeError):
            return None
