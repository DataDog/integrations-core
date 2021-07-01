# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
from os import listdir
from os.path import isfile, join

import jsonschema
import yaml

from .....constants import get_root
from ....console import abort, echo_failure, echo_info


def validate_profile(file, directory, verbose):

    profiles_list = find_profiles(file, directory)
    # contents = read_profile(profiles_list)
    # errors = validate_with_jsonschema(profiles_list, verbose)
    report_errors(profiles_list, verbose)


class Profile:
    def __init__(self):
        self.file_path = ""
        self.errors = []
        self.valid = True
        self.contents = ""

    def __repr__(self):
        return self.file_path

    def load_from_file(self, file_path):
        with open(file_path) as f:
            file_contents = yaml.safe_load(f.read())
            self.contents = file_contents
        if not file_contents:
            echo_failure("File contents returned None: " + self.file_path)
            abort()

    def validate(self):
        schema_file = join(
            get_root(),
            "datadog_checks_dev",
            "datadog_checks",
            "dev",
            "tooling",
            "commands",
            "meta",
            "snmp",
            "validators",
            "profile_schema.json",
        )
        with open(schema_file, "r") as f:
            contents = f.read()
            schema = json.loads(contents)
        validator = jsonschema.Draft7Validator(schema)

        errors = validator.iter_errors(self.contents)
        for error in errors:
            self.errors.append(error)

        if self.errors:
            self.valid = False


def construct_profile(file):
    profile = Profile()
    profile.file_path = file
    profile.load_from_file(file)
    profile.validate()
    return profile


def find_profiles(file, directory):
    if file:
        profiles_list = []
        profile = construct_profile(file)
        profiles_list.append(profile)
        return profiles_list

    dd_profiles_path = join("snmp", "datadog_checks", "snmp", "data", "profiles")
    profiles_path = join(get_root(), dd_profiles_path)

    if directory:
        profiles_path = directory
    profiles_list = get_all_profiles_from_dir(profiles_path)
    return profiles_list


def get_all_profiles_from_dir(directory):
    profiles_list = []
    profiles_path = directory
    dir_contents = [file for file in listdir(profiles_path) if isfile(join(profiles_path, file))]
    for file in dir_contents:
        file_path = join(profiles_path, file)
        profile = construct_profile(file_path)
        profiles_list.append(profile)
    return profiles_list


def report_errors(profiles_list, verbose):
    error_list = collect_invalid_profiles(profiles_list)
    valid_profiles = collect_valid_profiles(profiles_list)
    if verbose:
        echo_info("The following profiles validated successfully: ")
        for profile in valid_profiles:
            echo_info(str(profile))
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


def collect_invalid_profiles(profiles_list):
    invalid_profiles = [profile for profile in profiles_list if profile.valid is False]
    return invalid_profiles


def collect_valid_profiles(profiles_list):
    valid_profiles = [profile for profile in profiles_list if profile.valid is True]
    return valid_profiles


def convert_to_yaml(error):
    json_error = json.loads(json.dumps(error))
    yaml_error = yaml.dump(json_error, indent=2)
    return yaml_error
