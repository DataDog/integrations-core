import click

from .....fs import dir_exists, file_exists
from ...console import CONTEXT_SETTINGS, abort, echo_failure
from . import validators


@click.command("validate-profile", short_help="Validate SNMP profiles", context_settings=CONTEXT_SETTINGS)
@click.option('-f', '--file', help="Path to a profile file to validate")
@click.option('-d', '--directory', help="Path to a directory of profiles to validate")
@click.option('-v', '--verbose', help="Increase verbosity of error messages", is_flag=True)
def validate_profile(file, directory, verbose):
    if file:
        if not file_exists(file):
            echo_failure("Profile file not found, or could not be read: " + file)
            abort()
    if directory:
        if not dir_exists(directory):
            echo_failure("Directory not found, or could not be read: " + directory)
            abort()
    validators.validate_profile(file, directory, verbose)
