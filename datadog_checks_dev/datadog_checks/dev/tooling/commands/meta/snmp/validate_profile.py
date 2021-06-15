import click

from ...console import CONTEXT_SETTINGS,echo_info

@click.command("validate-profile", short_help="Validate SNMP profiles", context_settings=CONTEXT_SETTINGS)
def validate_profile():
    echo_info("validate profile!")
