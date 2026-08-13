"""Main CLI entry point."""

import click

from covenant_cli.commands.init_project import init_command
from covenant_cli.commands.add_service import add_service_command
from covenant_cli.commands.status import status_command


@click.group()
@click.version_option(package_name="covenant-cli")
def cli():
    """Covenant CLI -- governed agents, from the first line.

    Scaffold projects with built-in governance, typed I/O,
    exit reports, and memory inheritance.
    """
    pass


cli.add_command(init_command, "init")
cli.add_command(add_service_command, "add-service")
cli.add_command(status_command, "status")


if __name__ == "__main__":
    cli()
