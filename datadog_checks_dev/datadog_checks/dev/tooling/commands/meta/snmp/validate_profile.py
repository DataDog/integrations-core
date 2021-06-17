# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
from os.path import isfile, join
from sys import exit

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
def validate_profile(file, directory):

    #validating multiple instances with same schema - use IValidator.validate method
    #jsonschema.validate validates schema before validating instance
    # https://python-jsonschema.readthedocs.io/en/stable/validate/
    profiles_list = find_profiles(file, directory)
    for profile_path in profiles_list:
        contents = read_profile(profile_path)
        validate_with_jsonschema(contents)

#validate profiles
#collect errors - tell which file is generating the error


def find_profiles(file, directory):
    # allow adding path to other profiles? ex rapdev profiles: https://files.rapdev.io/datadog/snmp-profiles.zip
    #sample profile for testing
    # will probably need a function like this: https://github.com/DataDog/integrations-core/blob/97b85017240fec523c4ce84351fa25b80ddb031b/datadog_checks_dev/datadog_checks/dev/tooling/utils.py#L232-L234

    # def get_jmx_metrics_file(check_name):
    # path = os.path.join(get_root(), check_name, 'datadog_checks', check_name, 'data', 'metrics.yaml')
    # return path, file_exists(path)

# useful functions for files: https://github.com/DataDog/integrations-core/blob/97b85017240fec523c4ce84351fa25b80ddb031b/datadog_checks_dev/datadog_checks/dev/fs.py

#default is snmp/data/profiles
#iterate through to yield filenames
    profiles_list = []
    if file:
        profiles_list.append(file)
        return profiles_list

    if directory:
        # profiles_path = os.path.join(get_root(), "snmp","datadog_checks", "snmp","data","profiles")
        # file_extensions = [".yaml", ".yml"] #use .lower()?
        # profiles_list = [f for f in os.listdir(profiles_path) if isfile(join(profiles_path, f))]

        # echo_info(get_root()) # returns /Users/laura.hampton/dd/integrations-extras, why?

        profiles_list = get_all_profiles_from_dir(directory)
        return profiles_list

    else:
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
        exit()
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
        exit()
    path_and_contents[profile_path] = file_contents

    return path_and_contents


def validate_with_jsonschema(path_and_contents):
    schema = get_profile_schema()
    validator = jsonschema.Draft7Validator(schema)
    errors_dict = {}
    for path in path_and_contents:
        errors = validator.iter_errors(path_and_contents[path])

    for error in errors:
        errors_dict[error] = path

    for el in errors_dict:
        echo_info(errors_dict[el])
        echo_info(el)


    return


    #validate profile structure
    #base profiles different from non-base?

