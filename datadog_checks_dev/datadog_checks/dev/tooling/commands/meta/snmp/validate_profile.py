# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import click
import jsonschema
import yaml

from ...console import CONTEXT_SETTINGS,echo_info, abort, echo_failure, echo_success

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

    with open("/Users/laura.hampton/Embed_June_21/Ddev_local/dd/integrations-core/snmp/datadog_checks/snmp/data/profiles/cisco-asa-5525.yaml", "r") as f:
        profile = yaml.safe_load(f.read()) #returns json object
        return profile


def get_profile_schema():
    #extends (optional)
    #device:
        #vendor
    #sysobjectid
    #validate the schema? https://python-jsonschema.readthedocs.io/en/stable/validate/#jsonschema.IValidator.check_schema
    #return jsonschema.Draft7Validator(
    return(
        {
    "$schema": "http://json-schema.org/draft-07/schema",
    "$id": "http://example.com/example.json",
    "type": "object",
    "title": "The root schema",
    "description": "The root schema comprises the entire JSON document.",
    "default": {},
        "required": [
        "extends",
        "device",
        "sysobjectid"
    ],
    "properties": {
        "extends": {
            "$id": "#/properties/extends",
            "type": "array",
            "title": "The extends schema",
            "description": "Base profiles this profile builds on",
            "default": [],
            "additionalItems": True,
            "items": {
                "$id": "#/properties/extends/items",
                "anyOf": [
                    {
                        "$id": "#/properties/extends/items/anyOf/0",
                        "type": "string",
                        "title": "The first anyOf schema",
                        "description": "An explanation about the purpose of this instance.",
                        "default": "",
                        "examples": [
                            "_base.yaml",
                            "_cisco - asa.yaml"
                        ]
                    }
                ]
            }
        },
        "device": {
            "$id": "#/properties/device",
            "type": "object",
            "title": "The device schema",
            "description": "Device properties",
            "default": {},
            "examples": [
                {
                    "vendor": "cisco"
                }
            ],
            "required": [
                "vendor"
            ],
            "properties": {
                "vendor": {
                    "$id": "#/properties/device/properties/vendor",
                    "type": "string",
                    "title": "The vendor schema",
                    "description": "The vendor of the device to be monitored",
                    "default": "",
                }
            },
            "additionalProperties": True
        },
        "sysobjectid": {
            "$id": "#/properties/sysobjectid",
            "type": "string",
            "title": "The sysobjectid schema",
            "description": "Sysobjectid of the device",
            "default": "",
            "examples": [
                "1.3 .6 .1 .4 .1 .9 .1 .1408"
            ]
        }
    },
    "additionalProperties": True
})
        # {
        # "$schema": "http://json-schema.org/draft-07/schema#",
        # "title": "SNMP Integration Profile Schema",
        # "description": "Defines an SNMP integration profile",






    #validate profile structure
    #base profiles different from non-base?

