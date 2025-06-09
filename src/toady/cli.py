"""Main CLI interface for Toady."""

import click

from toady import __version__
from toady.commands.fetch import fetch
from toady.commands.reply import reply
from toady.commands.resolve import resolve
from toady.commands.schema import schema


@click.group()
@click.version_option(version=__version__, prog_name="toady")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Toady - GitHub PR review management tool.

    Efficiently manage GitHub pull request code reviews from the command line.
    """
    ctx.ensure_object(dict)


# Register commands
cli.add_command(fetch)
cli.add_command(reply)
cli.add_command(resolve)
cli.add_command(schema)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
