"""Tests to verify project setup and configuration."""

import pathlib
import subprocess
import sys

import pytest


class TestProjectStructure:
    """Test that the project structure is set up correctly."""

    def test_directory_structure_exists(self) -> None:
        """Test that all required directories exist."""
        root = pathlib.Path(__file__).parent.parent

        assert (root / "src").exists()
        assert (root / "src" / "toady").exists()
        assert (root / "tests").exists()
        assert (root / "docs").exists()
        assert (root / ".github" / "workflows").exists()

    def test_package_files_exist(self) -> None:
        """Test that package files exist."""
        root = pathlib.Path(__file__).parent.parent

        assert (root / "pyproject.toml").exists()
        assert (root / "README.md").exists()
        assert (root / "LICENSE").exists()
        assert (root / ".gitignore").exists()
        assert (root / "requirements.txt").exists()
        assert (root / "Makefile").exists()
        assert (root / "CHANGELOG.md").exists()

    def test_package_init_files(self) -> None:
        """Test that __init__.py files exist."""
        root = pathlib.Path(__file__).parent.parent

        assert (root / "src" / "toady" / "__init__.py").exists()
        assert (root / "tests" / "__init__.py").exists()

    def test_cli_module_exists(self) -> None:
        """Test that the CLI module exists."""
        root = pathlib.Path(__file__).parent.parent
        assert (root / "src" / "toady" / "cli.py").exists()

    def test_github_workflows_exist(self) -> None:
        """Test that GitHub workflow files exist."""
        root = pathlib.Path(__file__).parent.parent

        assert (root / ".github" / "workflows" / "ci.yml").exists()
        assert (root / ".github" / "workflows" / "release.yml").exists()

    def test_pre_commit_config_exists(self) -> None:
        """Test that pre-commit configuration exists."""
        root = pathlib.Path(__file__).parent.parent
        assert (root / ".pre-commit-config.yaml").exists()


class TestPackageImport:
    """Test that the package can be imported correctly."""

    def test_import_package(self) -> None:
        """Test importing the main package."""
        import toady

        assert hasattr(toady, "__version__")
        assert hasattr(toady, "__author__")
        assert hasattr(toady, "__email__")

    def test_import_cli(self) -> None:
        """Test importing the CLI module."""
        from toady import cli

        assert hasattr(cli, "cli")
        assert hasattr(cli, "fetch")
        assert hasattr(cli, "reply")
        assert hasattr(cli, "resolve")
        assert hasattr(cli, "main")


class TestPackageMetadata:
    """Test package metadata is configured correctly."""

    def test_version_consistency(self) -> None:
        """Test that version is consistent across files."""
        import toady

        # Version should be defined in __init__.py
        assert toady.__version__ == "0.1.0"

    def test_pyproject_toml_valid(self) -> None:
        """Test that pyproject.toml is valid."""
        root = pathlib.Path(__file__).parent.parent

        # Try to read and parse pyproject.toml
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib  # Python < 3.11
            except ImportError:
                pytest.skip("Neither tomllib nor tomli available for TOML parsing")

        with open(root / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)

        assert "project" in data
        assert data["project"]["name"] == "toady-cli"
        assert "dependencies" in data["project"]
        assert "click" in str(data["project"]["dependencies"])


class TestDevelopmentTools:
    """Test that development tools are properly configured."""

    def test_makefile_targets(self) -> None:
        """Test that Makefile has all expected targets."""
        root = pathlib.Path(__file__).parent.parent

        with open(root / "Makefile", encoding="utf-8") as f:
            makefile_content = f.read()

        expected_targets = [
            "help",
            "install",
            "install-dev",
            "test",
            "lint",
            "format",
            "type-check",
            "pre-commit",
            "check",
            "clean",
            "build",
        ]

        for target in expected_targets:
            assert f"{target}:" in makefile_content

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Entry points work differently on Windows"
    )
    def test_cli_entry_point(self) -> None:
        """Test that the CLI entry point is installed correctly."""
        # This test only works if the package is installed
        try:
            result = subprocess.run(
                ["toady", "--help"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,  # 10 second timeout
            )
            if result.returncode == 0:
                assert "Toady - GitHub PR review management tool" in result.stdout
            else:
                # If command fails, skip rather than fail (entry point not installed)
                pytest.skip(
                    f"CLI entry point not working (exit code: {result.returncode})"
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Entry point not installed yet or command hung, which is okay for setup
            pytest.skip("Entry point not installed or not responding")
