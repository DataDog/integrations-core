# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import click
import jsonschema
import os
from os.path import isfile, join
import yaml

from ...console import CONTEXT_SETTINGS,echo_info, abort, echo_failure, echo_success
from datadog_checks.dev.tooling.commands.meta.snmp.snmp_profile_schema import get_profile_schema
from ....constants import get_root
from .....fs import dir_exists, path_join, read_file, file_exists

@click.command("validate-profile", short_help="Validate SNMP profiles", context_settings=CONTEXT_SETTINGS)
@click.option('--file', help="Path to a profile file to validate")
def validate_profile(file):
    #jsonschema.validate(instance=read_profiles(), schema=get_profile_schema())
    #validating multiple instances with same schema - use IValidator.validate method
    #jsonschema.validate validates schema before validating instance
    # https://python-jsonschema.readthedocs.io/en/stable/validate/

    profile_list = read_profiles(file)
    for profile in profile_list:
        with open(profile) as f:
            contents = yaml.safe_load(f.read())
            result = jsonschema.validate(schema=get_profile_schema(), instance=contents)
            echo_info(profile)

    return result

    #collect errors
    # tell which file is generating the error



def read_profiles(file):
    # allow adding path to other profiles? ex rapdev profiles: https://files.rapdev.io/datadog/snmp-profiles.zip
    #sample profile for testing
    # will probably need a function like this: https://github.com/DataDog/integrations-core/blob/97b85017240fec523c4ce84351fa25b80ddb031b/datadog_checks_dev/datadog_checks/dev/tooling/utils.py#L232-L234

    # def get_jmx_metrics_file(check_name):
    # path = os.path.join(get_root(), check_name, 'datadog_checks', check_name, 'data', 'metrics.yaml')
    # return path, file_exists(path)

# useful functions for files: https://github.com/DataDog/integrations-core/blob/97b85017240fec523c4ce84351fa25b80ddb031b/datadog_checks_dev/datadog_checks/dev/fs.py

#default is snmp/data/profiles
#iterate through to yield filenames


    if not file:
        # profiles_path = os.path.join(get_root(), "snmp","datadog_checks", "snmp","data","profiles")
        # file_extensions = [".yaml", ".yml"] #use .lower()?
        # profiles_list = [f for f in os.listdir(profiles_path) if isfile(join(profiles_path, f))]

        # echo_info(get_root()) # returns /Users/laura.hampton/dd/integrations-extras, why?
        profiles_list = []
        profiles_path = os.path.join("dd", "integrations-core", "snmp","datadog_checks","snmp","data","profiles")
        dir_contents = [file for file in os.listdir(profiles_path) if isfile(join(profiles_path, file))]
        for profile in dir_contents:
            profiles_list.append(os.path.join(profiles_path,profile))


        #yield profiles?

    #if file:
    #with open(file, "r") as f:
    # with open("good_yaml.yaml") as f:
    #     profile = yaml.safe_load(f.read()) #returns json object


    return profiles_list #return a list of profiles








    #validate profile structure
    #base profiles different from non-base?

