
import os
from os.path import isfile, join


import click


from ..constants import get_root
from ..commands.console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success
from ...fs import file_exists
from validate_profile import validate_profile

@click.command("validate-profile", short_help="Validate SNMP profiles", context_settings=CONTEXT_SETTINGS)
@click.option('-f', '--file', help="Path to a profile file to validate")
@click.option('-d', '--directory', help="Path to a directory of profiles to validate")
@click.option('-v', '--verbose', help="Increase verbosity of error messages", is_flag=True)
