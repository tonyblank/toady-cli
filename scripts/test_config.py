#!/usr/bin/env python3
"""
Advanced Test Configuration and Runner for Toady CLI

This script provides advanced testing capabilities including:
- Test suite analysis and reporting
- Performance benchmarking
- Coverage analysis and reporting
- Test environment validation
- CI/CD integration helpers
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict


class TestConfig:
    """Advanced test configuration and management."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests"
        self.src_dir = project_root / "src"
        self.htmlcov_dir = project_root / "htmlcov"
        self.reports_dir = project_root / "test-reports"

    def setup_test_environment(self) -> bool:
        """Set up optimal test environment."""
        print("🔧 Setting up test environment...")

        # Create necessary directories
        self.reports_dir.mkdir(exist_ok=True)
        self.htmlcov_dir.mkdir(exist_ok=True)

        # Validate test structure
        if not self.test_dir.exists():
            print("❌ Tests directory not found!")
            return False

        if not self.src_dir.exists():
            print("❌ Source directory not found!")
            return False

        print("✅ Test environment ready")
        return True

    def run_fast_tests(self) -> int:
        """Run only fast unit tests."""
        print("🚀 Running fast test suite...")
        cmd = [
            "pytest",
            "-x",  # Stop on first failure
            "-q",  # Quiet output
            "--tb=short",
            "-m",
            "unit and not slow",
            "--disable-warnings",
        ]
        return subprocess.call(cmd)

    def run_full_test_suite(self) -> int:
        """Run complete test suite with coverage."""
        print("🧪 Running full test suite...")
        cmd = [
            "pytest",
            "--cov=toady",
            "--cov-branch",
            "--cov-report=term-missing:skip-covered",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-report=json:test-reports/coverage.json",
            "--cov-fail-under=80",
            "--durations=10",
            "--tb=short",
            "-v",
        ]
        return subprocess.call(cmd)

    def run_integration_tests(self) -> int:
        """Run integration tests only."""
        print("🔗 Running integration tests...")
        cmd = [
            "pytest",
            "-m",
            "integration",
            "--tb=short",
            "-v",
        ]
        return subprocess.call(cmd)

    def run_performance_tests(self) -> int:
        """Run performance benchmarks."""
        print("⚡ Running performance tests...")
        cmd = [
            "pytest",
            "-m",
            "slow",
            "--benchmark-only",
            "--benchmark-sort=mean",
            "--benchmark-json=test-reports/benchmark.json",
            "--tb=short",
        ]
        return subprocess.call(cmd)

    def analyze_test_suite(self) -> Dict[str, Any]:
        """Analyze test suite structure and metrics."""
        print("📊 Analyzing test suite...")

        analysis = {
            "total_test_files": 0,
            "total_test_functions": 0,
            "test_markers": {},
            "test_categories": {},
            "coverage_data": {},
        }

        # Count test files and functions
        # Search for both test_*.py and *_test.py patterns as defined in pytest.ini
        test_patterns = ["test_*.py", "*_test.py"]
        processed_files = set()  # Avoid double-counting files that match both patterns

        for pattern in test_patterns:
            for test_file in self.test_dir.rglob(pattern):
                if test_file in processed_files:
                    continue
                processed_files.add(test_file)
                analysis["total_test_files"] += 1

                # Read file and count test functions
                try:
                    content = test_file.read_text()
                    test_functions = [
                        line
                        for line in content.split("\n")
                        if line.strip().startswith("def test_")
                    ]
                    analysis["total_test_functions"] += len(test_functions)

                    # Count markers with safe splitting to avoid IndexError
                    for line in content.split("\n"):
                        line = line.strip()
                        if line.startswith("@pytest.mark."):
                            parts = line.split(".")
                            if len(parts) >= 3:
                                marker = parts[2].split("(")[0]
                                analysis["test_markers"][marker] = (
                                    analysis["test_markers"].get(marker, 0) + 1
                                )

                except Exception as e:
                    print(f"Warning: Could not analyze {test_file}: {e}")

        # Load coverage data if available
        coverage_file = self.reports_dir / "coverage.json"
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    analysis["coverage_data"] = {
                        "total_coverage": coverage_data.get("totals", {}).get(
                            "percent_covered", 0
                        ),
                        "branch_coverage": coverage_data.get("totals", {}).get(
                            "percent_covered_display", "N/A"
                        ),
                        "missing_lines": coverage_data.get("totals", {}).get(
                            "missing_lines", 0
                        ),
                    }
            except Exception as e:
                print(f"Warning: Could not load coverage data: {e}")

        return analysis

    def generate_test_report(self) -> None:
        """Generate comprehensive test report."""
        print("📝 Generating test report...")

        analysis = self.analyze_test_suite()

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "project": "toady-cli",
            "test_suite_analysis": analysis,
            "configuration": {
                "pytest_version": self._get_pytest_version(),
                "python_version": (
                    f"{sys.version_info.major}.{sys.version_info.minor}."
                    f"{sys.version_info.micro}"
                ),
                "coverage_threshold": 80,
            },
        }

        # Save report
        report_file = self.reports_dir / "test_analysis.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"📊 Test report saved to: {report_file}")
        self._print_analysis_summary(analysis)

    def _get_pytest_version(self) -> str:
        """Get pytest version."""
        try:
            result = subprocess.run(
                ["pytest", "--version"], capture_output=True, text=True
            )
            return result.stdout.split()[1] if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def _print_analysis_summary(self, analysis: Dict[str, Any]) -> None:
        """Print analysis summary to console."""
        print("\n" + "=" * 60)
        print("🧪 TEST SUITE ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"📁 Total test files: {analysis['total_test_files']}")
        print(f"🧪 Total test functions: {analysis['total_test_functions']}")

        if analysis["test_markers"]:
            print("\n🏷️  Test markers:")
            for marker, count in sorted(analysis["test_markers"].items()):
                print(f"   • {marker}: {count}")

        if analysis["coverage_data"]:
            print("\n📊 Coverage:")
            for key, value in analysis["coverage_data"].items():
                print(f"   • {key.replace('_', ' ').title()}: {value}")

        print("=" * 60)

    def validate_test_environment(self) -> bool:
        """Validate test environment and dependencies."""
        print("🔍 Validating test environment...")

        checks = [
            ("pytest", ["pytest", "--version"]),
            ("coverage", ["coverage", "--version"]),
            ("source code", None),  # Custom check
            ("test structure", None),  # Custom check
        ]

        all_good = True

        for name, cmd in checks:
            if cmd:
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        print(f"   ✅ {name}: OK")
                    else:
                        print(f"   ❌ {name}: Failed")
                        all_good = False
                except Exception as e:
                    print(f"   ❌ {name}: Error - {e}")
                    all_good = False
            else:
                # Custom checks
                if name == "source code":
                    if self.src_dir.exists() and (self.src_dir / "toady").exists():
                        print(f"   ✅ {name}: OK")
                    else:
                        print(f"   ❌ {name}: Source structure invalid")
                        all_good = False
                elif name == "test structure":
                    if self.test_dir.exists() and list(
                        self.test_dir.rglob("test_*.py")
                    ):
                        print(f"   ✅ {name}: OK")
                    else:
                        print(f"   ❌ {name}: No test files found")
                        all_good = False

        return all_good


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Advanced test configuration and runner for Toady CLI"
    )
    parser.add_argument(
        "action",
        choices=[
            "setup",
            "fast",
            "full",
            "integration",
            "performance",
            "analyze",
            "report",
            "validate",
        ],
        help="Action to perform",
    )
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )

    args = parser.parse_args()

    config = TestConfig(args.project_root)

    if args.action == "setup":
        success = config.setup_test_environment()
        sys.exit(0 if success else 1)
    elif args.action == "fast":
        sys.exit(config.run_fast_tests())
    elif args.action == "full":
        sys.exit(config.run_full_test_suite())
    elif args.action == "integration":
        sys.exit(config.run_integration_tests())
    elif args.action == "performance":
        sys.exit(config.run_performance_tests())
    elif args.action == "analyze":
        analysis = config.analyze_test_suite()
        config._print_analysis_summary(analysis)
    elif args.action == "report":
        config.generate_test_report()
    elif args.action == "validate":
        success = config.validate_test_environment()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
