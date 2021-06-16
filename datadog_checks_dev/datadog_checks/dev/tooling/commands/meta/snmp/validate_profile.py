# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import click
import jsonschema
import yaml

from ...console import CONTEXT_SETTINGS,echo_info, abort, echo_failure, echo_success
from datadog_checks.dev.tooling.commands.meta.snmp.snmp_profile_schema import get_profile_schema
from ....constants import get_root

@click.command("validate-profile", short_help="Validate SNMP profiles", context_settings=CONTEXT_SETTINGS)
@click.option('--file', help="Path to a profile file to validate")
def validate_profile(file):
    #jsonschema.validate(instance=read_profiles(), schema=get_profile_schema())
    #validating multiple instances with same schema - use IValidator.validate method
    #jsonschema.validate validates schema before validating instance
    # https://python-jsonschema.readthedocs.io/en/stable/validate/

    result = jsonschema.validate(schema=get_profile_schema(), instance=read_profiles(file))

    return type(result)

    #collect errors



def read_profiles(file):
    # allow adding path to other profiles? ex rapdev profiles: https://files.rapdev.io/datadog/snmp-profiles.zip
    #sample profile for testing
    # will probably need a function like this: https://github.com/DataDog/integrations-core/blob/97b85017240fec523c4ce84351fa25b80ddb031b/datadog_checks_dev/datadog_checks/dev/tooling/utils.py#L232-L234

# useful functions for files: https://github.com/DataDog/integrations-core/blob/97b85017240fec523c4ce84351fa25b80ddb031b/datadog_checks_dev/datadog_checks/dev/fs.py


    with open(file, "r") as f:
        profile = yaml.safe_load(f.read()) #returns json object


        return profile








    #validate profile structure
    #base profiles different from non-base?

