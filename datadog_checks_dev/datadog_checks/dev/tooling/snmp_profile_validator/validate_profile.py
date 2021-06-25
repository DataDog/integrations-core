# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
import os
from os.path import isfile, join

import click
import jsonschema
import yaml

from ..constants import get_root
from ..commands.console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success


@click.command("validate-profile", short_help="Validate SNMP profiles", context_settings=CONTEXT_SETTINGS)
@click.option('-f', '--file', help="Path to a profile file to validate")
@click.option('-d', '--directory', help="Path to a directory of profiles to validate")
@click.option('-v', '--verbose', help="Increase verbosity of error messages", is_flag=True)
def validate_profile(file, directory, verbose):
    profiles_list = find_profiles(file, directory)
    contents = read_profile(profiles_list)
    errors = validate_with_jsonschema(contents, verbose)
    produce_errors(errors, verbose)


class Profile:
    def __init__(self):
        self.file_path = ""
        self.errors = []
        self.invalid = False
        self.contents = ""

    def __repr__(self):
        return self.file_path


def find_profiles(file, directory):
    profiles_list = []
    profile = Profile()
    if file:
        profile.file_path = file
        profiles_list.append(profile)
        return profiles_list

    if directory:
        profiles_list = get_all_profiles_from_dir(directory)
        return profiles_list

    profiles_path = os.path.join(get_root(), "snmp", "datadog_checks", "snmp", "data", "profiles")
    profiles_list = [f for f in os.listdir(profiles_path) if isfile(join(profiles_path, f))]
    profiles_path = os.path.join(get_root(), "snmp", "datadog_checks", "snmp", "data", "profiles")
    profiles_list = get_all_profiles_from_dir(profiles_path)
    return profiles_list

    return profiles_list


def get_all_profiles_from_dir(directory):
    profiles_list = []
    profiles_path = directory
    try:
        dir_contents = [file for file in os.listdir(profiles_path) if isfile(join(profiles_path, file))]
    except FileNotFoundError:
        echo_failure("Directory not found, or could not be read")
        abort()
    for file in dir_contents:
        profile = Profile()
        profile.file_path = os.path.join(profiles_path, file)
        profiles_list.append(profile)
    return profiles_list


def read_profile(profiles_list):
    read_profiles = []
    for profile in profiles_list:
        try:
            with open(profile.file_path) as f:
                file_contents = yaml.safe_load(f.read())
                profile.contents = file_contents
        except OSError:
            echo_failure("Profile file not found, or could not be read")
            abort()
        if not file_contents:
            echo_failure("File contents returned None: " + str(profile))
            abort()
        read_profiles.append(profile)

    return read_profiles


def validate_with_jsonschema(profiles_list, verbose):
    schema_file = os.path.join(
        get_root(),
        "datadog_checks_dev",
        "datadog_checks",
        "dev",
        "tooling",
        "snmp_profile_validator",
        "snmp_profile.json",
    )
    with open(schema_file, "r") as f:
        contents = f.read()
        schema = json.loads(contents)
    validator = jsonschema.Draft7Validator(schema)
    for profile in profiles_list:
        if verbose:
            echo_info("Validating file: " + profile.file_path)
        errors = validator.iter_errors(profile.contents)
    for error in errors:
        profile.errors.append(error)

    # TODO - condition if there are no errors found
    return profiles_list


def produce_errors(profiles_list, verbose):
    error_list = []
    for profile in profiles_list:
        if profile.errors:
            error_list.append(profile)
            profiles_list.remove(profile)
    if verbose:
        for profile in profiles_list:
            echo_success("Profile validated successfully: " + str(profile))
    if error_list:
        for profile in error_list:
            echo_failure("Error found in profile: " + str(profile))
            for error in profile.errors:
                yaml_error = convert_to_yaml(error.instance)
                echo_failure("The file failed to parse near these lines: " + "\n" + yaml_error)
                echo_failure(error.message)

                if verbose:
                    echo_failure("Full error message: ")
                    echo_failure(error)
        abort()


def convert_to_yaml(error):
    json_error = json.loads(json.dumps(error))
    yaml_error = yaml.dump(json_error, indent=2)
    return yaml_error
