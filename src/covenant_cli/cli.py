"""Main CLI entry point."""

import click

from covenant_cli.commands.init_project import init_command
from covenant_cli.commands.add_service import add_service_command
from covenant_cli.commands.status import status_command
from covenant_cli.commands.remember import remember_command
from covenant_cli.commands.audit import audit_command


@click.group()
@click.version_option(package_name="covenant-cli")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.pass_context
def cli(ctx, verbose):
    """Covenant CLI -- governed agents, from the first line.

    Scaffold projects with built-in governance, typed I/O,
    exit reports, and memory inheritance.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


cli.add_command(init_command, "init")
cli.add_command(add_service_command, "add-service")
cli.add_command(status_command, "status")
cli.add_command(remember_command, "remember")
cli.add_command(audit_command, "audit")


if __name__ == "__main__":
    cli()
