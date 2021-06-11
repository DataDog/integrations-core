# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import jsonschema


def get_manifest_schema():
    return jsonschema.Draft7Validator(
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Integration Manifest Schema",
            "description": "Defines the various components of an integration",
            "type": "object",
            "properties": {
                "display_name": {
                    "description": "The human readable name of this integration",
                    "type": "string",
                    "pattern": "^[\u0000-\u007F]*$",
                    "minLength": 1,
                },
                "maintainer": {
                    "description": "The email address for the maintainer of this integration",
                    "type": "string",
                    "format": "email",
                },
                "manifest_version": {"description": "The schema version of this manifest", "type": "string"},
                "name": {
                    "description": "The name of this integration",
                    "type": "string",
                    "minLength": 1,
                    "pattern": "^[\u0000-\u007F]*$",
                },
                "metric_prefix": {
                    "description": "The prefix for metrics being emitted from this integration",
                    "type": "string",
                    "pattern": "^[\u0000-\u007F]*$",
                },
                "metric_to_check": {
                    "description": "The metric to use to determine the health of this integration",
                    "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
                    "pattern": "^[\u0000-\u007F]*$",
                },
                "creates_events": {"description": "Whether or not this integration emits events", "type": "boolean"},
                "short_description": {
                    "description": "Brief description of this integration",
                    "type": "string",
                    "pattern": "^[\u0000-\u007F]*$",
                    "minLength": 1,
                    "maxLength": 80,
                },
                "guid": {
                    "description": "A GUID for this integration",
                    "type": "string",
                    "pattern": "^[\u0000-\u007F]*$",
                    "minLength": 1,
                },
                "support": {
                    "description": "The support type for this integration, one of `core`, `contrib`, or `partner`",
                    "type": "string",
                    "enum": ["core", "contrib", "partner"],
                },
                "supported_os": {
                    "description": "The supported Operating Systems for this integration",
                    "type": "array",
                    "items": {"type": "string", "enum": ["linux", "mac_os", "windows"]},
                },
                "public_title": {
                    "description": "A human readable public title of this integration",
                    "type": "string",
                    "minLength": 1,
                },
                "categories": {
                    "description": "The categories of this integration",
                    "type": "array",
                    "items": {"type": "string", "pattern": "^[\u0000-\u007F]*$"},
                },
                "type": {"description": "The type of this integration", "type": "string", "enum": ["check", "crawler"]},
                "is_public": {"description": "Whether or not this integration is public", "type": "boolean"},
                "integration_id": {
                    "description": "The string identifier for this integration",
                    "type": "string",
                    "pattern": "^[a-z][a-z0-9-]{0,254}(?<!-)$",
                },
                "assets": {
                    "description": "An object containing the assets for an integration",
                    "type": "object",
                    "properties": {
                        "monitors": {"type": "object"},
                        "dashboards": {"type": "object"},
                        "service_checks": {
                            "type": "string",
                            "pattern": "^[\u0000-\u007F]*$",
                            "description": "Relative path to the json file containing service check metadata",
                        },
                        "metrics_metadata": {
                            "type": "string",
                            "pattern": "^[\u0000-\u007F]*$",
                            "description": "Relative path to the metrics metadata.csv file.",
                        },
                        "logs": {
                            "type": "object",
                            "properties": {
                                "source": {
                                    "type": "string",
                                    "pattern": "^[\u0000-\u007F]*$",
                                    "description": "The log pipeline identifier corresponding to this integration",
                                }
                            },
                        },
                    },
                    "required": ["monitors", "dashboards", "service_checks"],
                },
            },
            "allOf": [
                {
                    "if": {"properties": {"support": {"const": "core"}}},
                    "then": {
                        "properties": {"maintainer": {"pattern": "help@datadoghq.com"}},
                        "not": {
                            "anyOf": [{"required": ["author"]}, {"required": ["pricing"]}, {"required": ["terms"]}]
                        },
                    },
                },
                {
                    "if": {"properties": {"support": {"const": "contrib"}}},
                    "then": {"properties": {"maintainer": {"pattern": ".*"}}},
                },
                {
                    "if": {"properties": {"support": {"const": "partner"}}},
                    "then": {
                        "properties": {
                            "maintainer": {"pattern": ".*"},
                            "author": {
                                "description": "Information about the integration's author",
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "description": "The name of the company that owns this integration",
                                        "type": "string",
                                        "pattern": "^[\u0000-\u007F]*$",
                                    },
                                    "homepage": {
                                        "type": "string",
                                        "description": "The homepage of the company/product for this integration",
                                        "pattern": "^[\u0000-\u007F]*$",
                                    },
                                },
                            },
                            "pricing": {
                                "description": "Available pricing options",
                                "type": "array",
                                "minItems": 1,
                                "items": {
                                    "description": "Attributes of pricing plans available for this integration",
                                    "type": "object",
                                    "properties": {
                                        "billing_type": {
                                            "description": "The billing model for this integration",
                                            "type": "string",
                                            "enum": ["flat_fee", "free", "one_time", "tag_count"],
                                        },
                                        "unit_price": {
                                            "description": "The price per unit for this integration",
                                            "type": "number",
                                        },
                                        "unit_label": {
                                            "description": "The friendly, human readable, description of the tag",
                                            "type": "string",
                                            "pattern": "^[\u0000-\u007F]*$",
                                        },
                                        "metric": {"description": "The metric to use for metering", "type": "string"},
                                        "tag": {
                                            "description": ("The tag to use to count the number of billable units"),
                                            "type": "string",
                                            "pattern": "^[\u0000-\u007F]*$",
                                        },
                                    },
                                    "allOf": [
                                        {
                                            "if": {"properties": {"billing_type": {"const": "tag_count"}}},
                                            "then": {"required": ["unit_price", "unit_label", "metric", "tag"]},
                                        },
                                        {
                                            "if": {"properties": {"billing_type": {"const": "free"}}},
                                            "then": {
                                                "not": {
                                                    "anyOf": [
                                                        {"required": ["unit_label"]},
                                                        {"required": ["metric"]},
                                                        {"required": ["tag"]},
                                                        {"required": ["unit_price"]},
                                                    ]
                                                }
                                            },
                                        },
                                        {
                                            "if": {"properties": {"billing_type": {"pattern": "flat_fee|one_time"}}},
                                            "then": {
                                                "not": {
                                                    "anyOf": [
                                                        {"required": ["unit_label"]},
                                                        {"required": ["metric"]},
                                                        {"required": ["tag"]},
                                                    ]
                                                },
                                                "required": ["unit_price"],
                                            },
                                        },
                                    ],
                                },
                            },
                            "terms": {
                                "description": "Attributes about terms for an integration",
                                "type": "object",
                                "properties": {
                                    "eula": {
                                        "description": "A link to a PDF file containing the EULA for this integration",
                                        "type": "string",
                                        "pattern": "^[\u0000-\u007F]*$",
                                    },
                                    "legal_email": {
                                        "description": "Email of the partner company to use for subscription purposes",
                                        "type": "string",
                                        "format": "email",
                                        "minLength": 1,
                                    },
                                },
                                "required": ["eula", "legal_email"],
                            },
                        },
                        "required": ["author", "pricing", "terms"],
                    },
                },
            ],
            "required": [
                # Make metric_to_check and metric_prefix mandatory when all integration are fixed
                'assets',
                'categories',
                'creates_events',
                'display_name',
                'guid',
                'integration_id',
                'is_public',
                'maintainer',
                'manifest_version',
                'name',
                'public_title',
                'short_description',
                'support',
                'supported_os',
                'type',
            ],
        }
    )
