#!/usr/bin/env python3
"""
Comprehensive CI/CD Check Runner for Toady CLI

This script provides elegant CI/CD pipeline execution with:
- Beautiful progress reporting and status updates
- Comprehensive health checks and validations
- Performance timing and metrics collection
- Elegant error handling and failure reporting
- Full integration with make commands
"""

import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


class Colors:
    """ANSI color codes for beautiful terminal output."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class CIRunner:
    """Elegant CI/CD pipeline runner with comprehensive reporting."""

    def __init__(self, project_root: Path, verbose: bool = False):
        self.project_root = project_root
        self.verbose = verbose
        self.start_time = time.time()
        self.check_results: dict[str, dict[str, Any]] = {}
        self.total_checks = 0
        self.passed_checks = 0
        self.failed_checks = 0

    def print_header(self, title: str) -> None:
        """Print elegant section header."""
        width = 80
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * width}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{title:^{width}}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'=' * width}{Colors.ENDC}\n")

    def print_step(self, step: str, description: str) -> None:
        """Print step with elegant formatting."""
        print(f"{Colors.OKCYAN}{Colors.BOLD}[{step}]{Colors.ENDC} {description}")

    def print_success(self, message: str) -> None:
        """Print success message."""
        print(f"   {Colors.OKGREEN}✅ {message}{Colors.ENDC}")

    def print_failure(self, message: str) -> None:
        """Print failure message."""
        print(f"   {Colors.FAIL}❌ {message}{Colors.ENDC}")

    def print_warning(self, message: str) -> None:
        """Print warning message."""
        print(f"   {Colors.WARNING}⚠️  {message}{Colors.ENDC}")

    def print_info(self, message: str) -> None:
        """Print info message."""
        print(f"   {Colors.OKBLUE}ℹ️  {message}{Colors.ENDC}")

    def run_command(
        self,
        cmd: list[str],
        description: str,
        timeout: int = 300,
        check_output: bool = False,
    ) -> tuple[bool, str, float]:
        """Run command with timing and elegant error handling."""
        start_time = time.time()

        try:
            if self.verbose:
                self.print_info(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root,
            )

            duration = time.time() - start_time

            if result.returncode == 0:
                self.print_success(f"{description} ({duration:.2f}s)")
                if check_output and result.stdout:
                    for line in result.stdout.strip().split("\n")[
                        -3:
                    ]:  # Show last 3 lines
                        self.print_info(line.strip())
                return True, result.stdout, duration
            else:
                self.print_failure(f"{description} (failed after {duration:.2f}s)")
                if result.stderr:
                    for line in result.stderr.strip().split("\n")[
                        :5
                    ]:  # Show first 5 error lines
                        print(f"      {Colors.FAIL}{line.strip()}{Colors.ENDC}")
                return False, result.stderr, duration

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.print_failure(f"{description} (timeout after {duration:.2f}s)")
            return False, f"Command timed out after {timeout}s", duration

        except Exception as e:
            duration = time.time() - start_time
            self.print_failure(f"{description} (error: {str(e)})")
            return False, str(e), duration

    def validate_environment(self) -> bool:
        """Validate development environment."""
        self.print_step("ENV", "Validating development environment")

        checks = [
            (["python3", "--version"], "Python 3 availability"),
            (["pytest", "--version"], "Pytest availability"),
            (["black", "--version"], "Black formatter availability"),
            (["ruff", "--version"], "Ruff linter availability"),
            (["mypy", "--version"], "MyPy type checker availability"),
            (["pre-commit", "--version"], "Pre-commit hooks availability"),
        ]

        all_passed = True
        for cmd, desc in checks:
            success, output, duration = self.run_command(cmd, desc, timeout=30)
            if not success:
                all_passed = False

        return all_passed

    def check_code_formatting(self) -> bool:
        """Check code formatting with Black."""
        self.print_step("FMT", "Checking code formatting")

        success, output, duration = self.run_command(
            ["black", "--check", "src", "tests"], "Code formatting check"
        )

        self.check_results["formatting"] = {
            "passed": success,
            "duration": duration,
            "output": output,
        }

        return success

    def check_linting(self) -> bool:
        """Check code linting with Ruff."""
        self.print_step("LINT", "Running code linting")

        success, output, duration = self.run_command(
            ["ruff", "check", "--no-fix", "src", "tests"], "Code linting check"
        )

        self.check_results["linting"] = {
            "passed": success,
            "duration": duration,
            "output": output,
        }

        return success

    def check_type_hints(self) -> bool:
        """Check type hints with MyPy."""
        self.print_step("TYPE", "Checking type hints")

        success, output, duration = self.run_command(
            ["mypy", "--strict", "--ignore-missing-imports", "src"], "Type checking"
        )

        self.check_results["typing"] = {
            "passed": success,
            "duration": duration,
            "output": output,
        }

        return success

    def run_tests(self) -> bool:
        """Run comprehensive test suite."""
        self.print_step("TEST", "Running comprehensive test suite")

        # Use exact same command as CI pipeline
        success, output, duration = self.run_command(
            [
                "pytest",
                "-v",
                "--cov=toady",
                "--cov-report=xml:coverage.xml",
                "--cov-report=term-missing",
            ],
            "Test suite execution (1132 tests - this may take several minutes)",
            timeout=600,  # 10 minutes for full test suite
            check_output=True,
        )

        # Parse coverage from output (pytest format)
        coverage_info = "Coverage information not available"
        if "TOTAL" in output:
            for line in output.split("\n"):
                if "TOTAL" in line and "%" in line:
                    # Extract coverage percentage from pytest output
                    parts = line.split()
                    if len(parts) >= 4 and parts[-1].endswith("%"):
                        coverage_info = f"Total coverage: {parts[-1]}"
                    break

        self.check_results["testing"] = {
            "passed": success,
            "duration": duration,
            "output": output,
            "coverage": coverage_info,
        }

        if success:
            self.print_info(coverage_info)

        return success

    def check_trailing_whitespace(self) -> bool:
        """Check for trailing whitespace."""
        self.print_step("WHITESPACE", "Checking trailing whitespace")

        success, output, duration = self.run_command(
            ["pre-commit", "run", "trailing-whitespace", "--all-files"],
            "Trailing whitespace check",
        )

        self.check_results["trailing_whitespace"] = {
            "passed": success,
            "duration": duration,
            "output": output,
        }

        return success

    def check_end_of_files(self) -> bool:
        """Check for proper end of files."""
        self.print_step("EOF", "Checking end of files")

        success, output, duration = self.run_command(
            ["pre-commit", "run", "end-of-file-fixer", "--all-files"],
            "End of file check",
        )

        self.check_results["end_of_files"] = {
            "passed": success,
            "duration": duration,
            "output": output,
        }

        return success

    def run_pre_commit_hooks(self) -> bool:
        """Run pre-commit hooks."""
        self.print_step("HOOKS", "Running pre-commit hooks")

        success, output, duration = self.run_command(
            ["pre-commit", "run", "--all-files"], "Pre-commit hooks execution"
        )

        self.check_results["pre_commit"] = {
            "passed": success,
            "duration": duration,
            "output": output,
        }

        return success

    def generate_summary_report(self) -> None:
        """Generate elegant summary report."""
        total_duration = time.time() - self.start_time

        self.print_header("🎯 CI/CD PIPELINE SUMMARY REPORT")

        # Overall status
        if self.failed_checks == 0:
            print(f"{Colors.OKGREEN}{Colors.BOLD}🎉 ALL CHECKS PASSED!{Colors.ENDC}")
            success_msg = (
                f"{Colors.OKGREEN}✨ Pipeline completed successfully in "
                f"{total_duration:.2f} seconds{Colors.ENDC}\n"
            )
            print(success_msg)
        else:
            print(f"{Colors.FAIL}{Colors.BOLD}💥 PIPELINE FAILED!{Colors.ENDC}")
            failure_msg = (
                f"{Colors.FAIL}❌ {self.failed_checks} of {self.total_checks} "
                f"checks failed{Colors.ENDC}\n"
            )
            print(failure_msg)

        # Detailed results
        print(f"{Colors.BOLD}📊 Detailed Results:{Colors.ENDC}")
        for check_name, result in self.check_results.items():
            status_icon = "✅" if result["passed"] else "❌"
            status_color = Colors.OKGREEN if result["passed"] else Colors.FAIL

            print(
                f"   {status_icon} {Colors.BOLD}{check_name.title():.<20}{Colors.ENDC} "
                f"{status_color}{result['duration']:.2f}s{Colors.ENDC}"
            )

        # Performance summary
        print(f"\n{Colors.BOLD}⚡ Performance Summary:{Colors.ENDC}")
        print(f"   • Total Duration: {total_duration:.2f} seconds")
        print(f"   • Checks Executed: {self.total_checks}")
        print(f"   • Success Rate: {(self.passed_checks/self.total_checks)*100:.1f}%")

        # Coverage information
        if (
            "testing" in self.check_results
            and "coverage" in self.check_results["testing"]
        ):
            print(f"   • {self.check_results['testing']['coverage']}")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{Colors.BOLD}🕒 Completed at:{Colors.ENDC} {timestamp}")

    def run_comprehensive_check(self) -> bool:
        """Run comprehensive CI/CD pipeline."""
        self.print_header("🚀 TOADY CLI - COMPREHENSIVE CI/CD PIPELINE")

        print(f"{Colors.BOLD}Project:{Colors.ENDC} {self.project_root.name}")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{Colors.BOLD}Started:{Colors.ENDC} {timestamp}")
        print(f"{Colors.BOLD}Mode:{Colors.ENDC} Comprehensive Quality Assurance")

        # Define check pipeline
        pipeline_steps = [
            ("Environment Validation", self.validate_environment),
            ("Code Formatting", self.check_code_formatting),
            ("Code Linting", self.check_linting),
            ("Type Checking", self.check_type_hints),
            ("Pre-commit Hooks", self.run_pre_commit_hooks),
            ("Test Suite", self.run_tests),
        ]

        self.total_checks = len(pipeline_steps)
        all_passed = True

        # Execute pipeline steps
        for step_name, step_func in pipeline_steps:
            try:
                success = step_func()

                if success:
                    self.passed_checks += 1
                else:
                    self.failed_checks += 1
                    all_passed = False

                    # Stop on first failure for fail-fast behavior
                    self.print_failure(
                        f"Pipeline stopped due to {step_name.lower()} failure"
                    )
                    break

            except Exception as e:
                self.print_failure(f"Unexpected error in {step_name}: {str(e)}")
                self.failed_checks += 1
                all_passed = False
                break

        # Generate final report
        self.generate_summary_report()

        return all_passed

    def run_fast_check(self) -> bool:
        """Run fast check pipeline (without full tests)."""
        self.print_header("⚡ TOADY CLI - FAST QUALITY CHECK")

        print(f"{Colors.BOLD}Project:{Colors.ENDC} {self.project_root.name}")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{Colors.BOLD}Started:{Colors.ENDC} {timestamp}")
        print(f"{Colors.BOLD}Mode:{Colors.ENDC} Fast Quality Check")

        # Define fast check pipeline
        pipeline_steps = [
            ("Environment Validation", self.validate_environment),
            ("Code Formatting", self.check_code_formatting),
            ("Code Linting", self.check_linting),
            ("Type Checking", self.check_type_hints),
            ("Trailing Whitespace", self.check_trailing_whitespace),
            ("End of Files", self.check_end_of_files),
        ]

        self.total_checks = len(pipeline_steps)
        all_passed = True

        for step_name, step_func in pipeline_steps:
            try:
                success = step_func()

                if success:
                    self.passed_checks += 1
                else:
                    self.failed_checks += 1
                    all_passed = False
                    self.print_failure(
                        f"Fast check stopped due to {step_name.lower()} failure"
                    )
                    break

            except Exception as e:
                self.print_failure(f"Unexpected error in {step_name}: {str(e)}")
                self.failed_checks += 1
                all_passed = False
                break

        self.generate_summary_report()
        return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Elegant CI/CD pipeline runner for Toady CLI"
    )
    parser.add_argument(
        "mode",
        choices=["full", "fast"],
        help="Check mode: full (all checks) or fast (no tests)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )

    args = parser.parse_args()

    runner = CIRunner(args.project_root, args.verbose)

    if args.mode == "full":
        success = runner.run_comprehensive_check()
    else:
        success = runner.run_fast_check()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
