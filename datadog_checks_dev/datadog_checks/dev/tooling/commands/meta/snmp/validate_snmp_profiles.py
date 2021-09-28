import click

from ...console import CONTEXT_SETTINGS, echo_failure, echo_info, echo_success, echo_warning
from . import validators
from .validators.utils import (
    exist_profile_in_path,
    get_all_profiles_directory,
    get_default_snmp_profiles_path,
    initialize_path,
)

MESSAGE_METHODS = {'success': echo_success, 'warning': echo_warning, 'failure': echo_failure, 'info': echo_info}


@click.command("validate-profile", short_help="Validate SNMP profiles", context_settings=CONTEXT_SETTINGS)
@click.option('-f', '--file', help="Path to a profile file to validate")
@click.option('-d', '--directory', help="Path to a directory of profiles to validate")
@click.option('-v', '--verbose', help="Increase verbosity of error messages", is_flag=True)
def validate_profile(file, directory, verbose):
    path = initialize_path(directory)

    if file:
        _validate_profile(file, path)

    else:
        if not directory:
            directory = get_default_snmp_profiles_path()

        all_profiles_directory = get_all_profiles_directory(directory)
        for profile in all_profiles_directory:
            echo_info("Start validation of profile {profile}:".format(profile=profile))
            _validate_profile(profile, path)

    echo_info("Starting validation of group of profiles")

    _validate_profile(file, path, group=True)


def _validate_profile(file, path, group=False):
    if not exist_profile_in_path(file, path) and not group:
        echo_failure("Profile file not found, or could not be read: " + str(file))
        return

    all_validators = validators.get_all_single_validators()
    if group:
        all_validators = validators.get_all_group_validators()
        if not file:
            file = ''

    report = validate_profile_from_validators(all_validators, file, path)

    show_report(report)


def validate_profile_from_validators(all_validators, file, path):
    display_queue = []
    failure = False

    for validator in all_validators:
        validator.validate(file, path)
        failure = validator.result.failed
        for msg_type, messages in validator.result.messages.items():
            for message in messages:
                display_queue.append((MESSAGE_METHODS[msg_type], message))
        if failure:
            break

    report_profile = {}
    report_profile['messages'] = display_queue
    report_profile['failed'] = failure

    return report_profile


def show_report(report):
    if report['failed']:
        echo_failure("FAILED")
    else:
        echo_success("Successfully validated")

    for display_func, message in report['messages']:
        display_func(message)
