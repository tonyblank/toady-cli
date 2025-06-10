"""Utilities for command implementations."""

import functools
from typing import Any, Callable

import click

from .error_handling import handle_error
from .exceptions import ToadyError


def handle_command_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle errors in command functions.

    This decorator catches ToadyError exceptions and handles them
    using the unified error handling system.

    Args:
        func: The command function to wrap.

    Returns:
        Wrapped function with error handling.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except ToadyError as e:
            # Get debug flag from context if available
            try:
                ctx = click.get_current_context(silent=True)
                debug = False
                if ctx and ctx.obj and isinstance(ctx.obj, dict):
                    debug = ctx.obj.get("debug", False)
            except Exception:
                debug = False

            handle_error(e, show_traceback=debug)
            # Note: handle_error calls sys.exit() and never returns
        except Exception:
            # For unexpected errors, let them bubble up to main()
            raise

    return wrapper


def validate_pr_number(pr_number: int) -> None:
    """Validate a PR number.

    Args:
        pr_number: The PR number to validate.

    Raises:
        click.BadParameter: If the PR number is invalid.
    """
    if pr_number <= 0:
        raise click.BadParameter("PR number must be positive", param_hint="--pr")

    # Enhanced PR number validation - GitHub PR numbers are typically much smaller
    MAX_REASONABLE_PR_NUMBER = 999999
    if pr_number > MAX_REASONABLE_PR_NUMBER:
        raise click.BadParameter(
            f"PR number appears unreasonably large "
            f"(maximum: {MAX_REASONABLE_PR_NUMBER})",
            param_hint="--pr",
        )


def validate_limit(limit: int, max_limit: int = 1000) -> None:
    """Validate a limit parameter.

    Args:
        limit: The limit value to validate.
        max_limit: Maximum allowed limit.

    Raises:
        click.BadParameter: If the limit is invalid.
    """
    if limit <= 0:
        raise click.BadParameter("Limit must be positive", param_hint="--limit")
    if limit > max_limit:
        raise click.BadParameter(
            f"Limit cannot exceed {max_limit}", param_hint="--limit"
        )
