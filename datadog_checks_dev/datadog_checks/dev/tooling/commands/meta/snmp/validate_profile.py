# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
import os
from os.path import isfile, join

import click
import jsonschema

import yaml

from ...console import CONTEXT_SETTINGS,echo_info, abort, echo_failure, echo_success
from datadog_checks.dev.tooling.commands.meta.snmp.snmp_profile_schema import get_profile_schema
from ....constants import get_root
from .....fs import dir_exists, path_join, read_file, file_exists

@click.command("validate-profile", short_help="Validate SNMP profiles", context_settings=CONTEXT_SETTINGS)
@click.option('--file', help="Path to a profile file to validate")
@click.option('--directory', help="Path to a directory of profiles to validate")
@click.option('--verbose', help="Increase verbosity of error messages", is_flag=True)
def validate_profile(file, directory, verbose):
    profiles_list = find_profiles(file, directory)
    for profile_path in profiles_list:
        contents = read_profile(profile_path)
        errors = validate_with_jsonschema(contents, verbose)

    produce_errors(errors, verbose)

def find_profiles(file, directory):
    profiles_list = []
    if file:
        profiles_list.append(file)
        return profiles_list

    if directory:
        profiles_list = get_all_profiles_from_dir(directory)
        return profiles_list

    else:
        profiles_path = os.path.join(get_root(), "snmp","datadog_checks", "snmp","data","profiles")
        file_extensions = [".yaml", ".yml"] #use .lower()?
        profiles_list = [f for f in os.listdir(profiles_path) if isfile(join(profiles_path, f))]
        profiles_path = os.path.join("dd", "integrations-core", "snmp","datadog_checks","snmp","data","profiles")
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
    for profile in dir_contents:
        profiles_list.append(os.path.join(profiles_path,profile))
    return profiles_list


def read_profile(profile_path):
    path_and_contents = {}
    try:
        with open(profile_path) as f:
            file_contents = yaml.safe_load(f.read())
    except OSError:
        echo_failure("Profile file not found, or could not be read")
        abort()
    path_and_contents[profile_path] = file_contents
    if not file_contents:
        echo_failure("File contents returned None: " + profile_path)
        abort()

    return path_and_contents


def validate_with_jsonschema(path_and_contents, verbose):
    schema_file = os.path.join(get_root(),"datadog_checks_dev", "datadog_checks", "dev", "tooling", "commands", "meta", "snmp","snmp_profile.json")
    with open(schema_file, "r") as f:
        contents = f.read()
        schema = json.loads(contents)
    validator = jsonschema.Draft7Validator(schema)
    errors_dict = {}
    valid_files = []
    for path in path_and_contents:
        if verbose:
            echo_info("Validating file: " + path)
        errors = validator.iter_errors(path_and_contents[path])
    for error in errors:
        errors_dict[error] = path



    #TODO - condition if there are no errors found
    return errors_dict

def produce_errors(errors_dict,verbose):
    for error in errors_dict:
        echo_failure("Error found in file: " + errors_dict[error])
        yaml_error = convert_to_yaml(error)
        echo_failure("The file failed to parse near these lines: " +"\n" + yaml_error)

        if verbose:
            echo_failure("Full error message: ")
            echo_failure(error.message)
    abort()

def convert_to_yaml(error):
    json_error = json.loads(json.dumps(error.instance))
    yaml_error = yaml.dump(json_error, indent=2)
    return yaml_error

#tomorrow - , remove hardcoded paths  check for duplicates? better errors,
#x return error code for CI
# open draft pr


#integrations-core validation only
#friendlier verbose error output - what was expected - expecting this, got this instead
# x sysobjectid can be an array instead of string



#good condition
# find errors in support cases
#group errors by file
#number of errors by file
# 0 errors found
# fix path to jsonschema and profiles
#check on extract tags pattern - check per dev documentation
# features not supported in core check - name but not oid
# https://docs.google.com/document/d/1OMMEOMuB9NWOz2uJgf89lNzudqHvQqGA-0Eeg8o81D0/edit#heading=h.klntf3xonn2j - raise warning on not supported? deprecated schema - create card

#report all errors for a file together, under the same filename?
# report files that passed validation
#translate json from error message into yaml, then find in file, potentially?


