import click

from .....fs import dir_exists, file_exists
from ...console import CONTEXT_SETTINGS, abort, echo_failure, echo_success, echo_warning, echo_info
from . import validators

from .validators.utils import (
    initialize_path,
    exist_profile_in_path
)


@click.command("validate-profile", short_help="Validate SNMP profiles", context_settings=CONTEXT_SETTINGS)
@click.option('-f', '--file', help="Path to a profile file to validate")
@click.option('-d', '--directory', help="Path to a directory of profiles to validate")
@click.option('-v', '--verbose', help="Increase verbosity of error messages", is_flag=True)
@click.option('-p', '--path', help="File containg the path of the directories of all profiles")
def validate_profile(file, directory, verbose, path):
    path = initialize_path(path, directory)

    if not exist_profile_in_path(file,path): 
        echo_failure("Profile file not found, or could not be read: " + file)
        abort()

    message_methods = {'success': echo_success, 'warning': echo_warning, 'failure': echo_failure, 'info': echo_info}
    
    all_validators = validators.get_all_validators()

    display_queue = []
    file_failures = 0
    file_fixed = False

    for validator in all_validators:
        validator.validate(file,directory,path)
        file_failures += 1 if validator.result.failed else 0
        file_fixed += 1 if validator.result.fixed else 0
        for msg_type, messages in validator.result.messages.items():
            for message in messages:
                display_queue.append((message_methods[msg_type], message))
    
    if file_failures > 0:
        echo_failure("FAILED")
    for display_func, message in display_queue:
        display_func(message)
    # validators.validate_profile(file, directory, verbose)
