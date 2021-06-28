
import os
from os.path import isfile, join


import click


from ..constants import get_root
from ..commands.console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success
from ...fs import file_exists, dir_exists
from .validate_profile import validate_profile

@click.command("validate-profile", short_help="Validate SNMP profiles", context_settings=CONTEXT_SETTINGS)
@click.option('-f', '--file', help="Path to a profile file to validate")
@click.option('-d', '--directory', help="Path to a directory of profiles to validate")
@click.option('-v', '--verbose', help="Increase verbosity of error messages", is_flag=True)
def click_options(file, directory, verbose):
    if file:
        if not file_exists(file):
            echo_failure("Profile file not found, or could not be read: " + file)
            abort()
    if directory:
        if not dir_exists(directory):
            echo_failure("Directory not found, or could not be read: " + directory)
            abort()
    validate_profile(file, directory, verbose)

#only click-related stuff in a separate file
#different click options for each validator - jsonschema, duplicates
# tests - unit tests independent of click


