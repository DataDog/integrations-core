# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import click
import jsonschema
import yaml

from ...console import CONTEXT_SETTINGS,echo_info, abort, echo_failure, echo_success
from datadog_checks.dev.tooling.commands.meta.snmp.snmp_profile_schema import get_profile_schema

@click.command("validate-profile", short_help="Validate SNMP profiles", context_settings=CONTEXT_SETTINGS)
def validate_profile():
    #jsonschema.validate(instance=read_profiles(), schema=get_profile_schema())
    #validating multiple instances with same schema - use IValidator.validate method
    #jsonschema.validate validates schema before validating instance
    # https://python-jsonschema.readthedocs.io/en/stable/validate/

    result = jsonschema.validate(schema=get_profile_schema(), instance=read_profiles())
    return type(result)

    #collect errors



def read_profiles():
    # allow adding path to other profiles? ex rapdev profiles: https://files.rapdev.io/datadog/snmp-profiles.zip
    #sample profile for testing
    # will probably need a function like this: https://github.com/DataDog/integrations-core/blob/97b85017240fec523c4ce84351fa25b80ddb031b/datadog_checks_dev/datadog_checks/dev/tooling/utils.py#L232-L234

    # with open("/Users/laura.hampton/Embed_June_21/Ddev_local/dd/integrations-core/snmp/datadog_checks/snmp/data/profiles/cisco-asa-5525.yaml", "r") as f:
    #     profile = yaml.safe_load(f.read()) #returns json object

    #     return profile


    with open("bad_1.yaml", "r") as f:
        profile = yaml.safe_load(f.read()) #returns json object


        return profile








    #validate profile structure
    #base profiles different from non-base?

