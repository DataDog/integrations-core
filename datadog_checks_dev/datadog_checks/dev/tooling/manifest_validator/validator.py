# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import abc
import os
import uuid
from collections import namedtuple
from typing import Dict

import jsonschema
import six

from datadog_checks.dev.tooling.constants import get_root
from datadog_checks.dev.tooling.git import content_changed
from datadog_checks.dev.tooling.utils import get_metadata_file, parse_version_parts, read_metadata_rows

FIELDS_NOT_ALLOWED_TO_CHANGE = ["integration_id", "display_name", "guid"]

METRIC_TO_CHECK_WHITELIST = {
    'openstack.controller',  # "Artificial" metric, shouldn't be listed in metadata file.
    'riakcs.bucket_list_pool.workers',  # RiakCS 2.1 metric, but metadata.csv lists RiakCS 2.0 metrics only.
}


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
                    "minLength": 1,
                },
                "maintainer": {
                    "description": "The email address for the maintainer of this integration",
                    "type": "string",
                    "format": "email",
                },
                "manifest_version": {"description": "The schema version of this manifest", "type": "string"},
                "name": {"description": "The name of this integration", "type": "string", "minLength": 1},
                "metric_prefix": {
                    "description": "The prefix for metrics being emitted from this integration",
                    "type": "string",
                },
                "metric_to_check": {
                    "description": "The metric to use to determine the health of this integration",
                    "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
                },
                "creates_events": {"description": "Whether or not this integration emits events", "type": "boolean"},
                "short_description": {
                    "description": "Brief description of this integration",
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 80,
                },
                "guid": {"description": "A GUID for this integration", "type": "string", "minLength": 1},
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
                    "items": {"type": "string"},
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
                            "description": "Relative path to the json file containing service check metadata",
                        },
                        "metrics_metadata": {
                            "type": "string",
                            "description": "Relative path to the metrics metadata.csv file.",
                        },
                        "logs": {
                            "type": "object",
                            "properties": {
                                "source": {
                                    "type": "string",
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
                                    },
                                    "homepage": {
                                        "type": "string",
                                        "description": "The homepage of the company/product for this integration",
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
                                        },
                                        "metric": {"description": "The metric to use for metering", "type": "string"},
                                        "tag": {
                                            "description": ("The tag to use to count the number of billable units"),
                                            "type": "string",
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


def is_metric_in_metadata_file(metric, check):
    """
    Return True if `metric` is listed in the check's `metadata.csv` file, False otherwise.
    """
    metadata_file = get_metadata_file(check)
    if not os.path.isfile(metadata_file):
        return False
    for _, row in read_metadata_rows(metadata_file):
        if row['metric_name'] == metric:
            return True
    return False


ValidationResult = namedtuple('ValidationResult', 'failed fixed messages')


@six.add_metaclass(abc.ABCMeta)
class ManifestValidator(object):
    def __init__(self, is_extras=False, is_marketplace=False):
        self.result = ValidationResult(
            failed=False, fixed=False, messages={'success': [], 'warning': [], 'failure': [], 'info': []}
        )
        self.is_extras = is_extras
        self.is_marketplace = is_marketplace

    def validate(self, check_name, manifest, should_fix):
        # type: (str, Dict, bool) -> ValidationResult
        """Validates the decoded manifest. Will perform inline changes if fix is true"""
        raise NotImplementedError

    def fail(self, error_message):
        self.result.failed = True
        self.result.messages['failure'].append(error_message)

    def fix(self, problem, solution):
        self.result.warning_msg = problem
        self.result.success_msg = solution
        self.result.fixed = True
        self.result.failed = False


class AttributesValidator(ManifestValidator):
    """ attributes are valid"""

    def validate(self, check_name, decoded, fix):
        errors = sorted(get_manifest_schema().iter_errors(decoded), key=lambda e: e.path)
        if errors:
            for error in errors:
                self.fail(f'  {"->".join(map(str, error.absolute_path))} Error: {error.message}')


class GUIDValidator(ManifestValidator):
    all_guids = {}

    def validate(self, check_name, decoded, fix):
        guid = decoded.get('guid')
        if guid in self.all_guids:
            output = f'  duplicate `guid`: `{guid}` from `{self.all_guids[guid]}`'
            if fix:
                new_guid = uuid.uuid4()
                self.all_guids[new_guid] = check_name
                decoded['guid'] = new_guid
                self.fix(output, f'  new `guid`: {new_guid}')
            else:
                self.fail(output)
        elif not guid or not isinstance(guid, str):

            output = '  required non-null string: guid'
            if fix:
                new_guid = uuid.uuid4()
                self.all_guids[new_guid] = check_name
                decoded['guid'] = new_guid
                self.fix(output, f'  new `guid`: {new_guid}')
            else:
                self.fail(output)
        else:
            self.result.failed = True
            self.all_guids[guid] = check_name
        return self.result


class ManifestVersionValidator(ManifestValidator):
    root = get_root()

    def validate(self, check_name, decoded, fix):
        # manifest_version
        correct_manifest_version = '1.0.0'
        manifest_version = decoded.get('manifest_version')
        version_parts = parse_version_parts(manifest_version)
        if len(version_parts) != 3:
            if not manifest_version:
                output = '  required non-null string: manifest_version'
            else:
                output = f'  invalid `manifest_version`: {manifest_version}'

            if fix:
                version_parts = parse_version_parts(correct_manifest_version)
                decoded['manifest_version'] = correct_manifest_version
                self.fix(output, f'  new `manifest_version`: {correct_manifest_version}')
            else:
                self.fail(output)

        if len(version_parts) == 3:
            about_exists = os.path.isfile(
                os.path.join(self.root, check_name, 'datadog_checks', check_name, '__about__.py')
            )
            if version_parts >= [1, 0, 0]:
                if 'version' in decoded and about_exists:
                    output = '  outdated field: version'

                    if fix:
                        del decoded['version']
                        self.fix(output, '  removed field: version')
                    else:
                        self.fail(output)
            elif about_exists:
                output = f'  outdated `manifest_version`: {manifest_version}'

                if fix:
                    decoded['manifest_version'] = correct_manifest_version
                    self.fix(output, f'  new `manifest_version`: {correct_manifest_version}')
                    if 'version' in decoded:
                        del decoded['version']
                        self.result.messages['success'].append('  removed field: version')
                else:
                    self.fail(output)
            else:
                version = decoded.get('version')
                version_parts = parse_version_parts(version)
                if len(version_parts) != 3:
                    if not version:
                        output = '  required non-null string: version'
                    else:
                        output = f'  invalid `version`: {version}'
                    self.fail(output)


class MaintainerValidator(ManifestValidator):
    def validate(self, check_name, decoded, fix):
        if not self.is_extras and not self.is_marketplace:
            correct_maintainer = 'help@datadoghq.com'
            maintainer = decoded.get('maintainer')
            if maintainer != correct_maintainer:
                output = f'  incorrect `maintainer`: {maintainer}'
                if fix:
                    decoded['maintainer'] = correct_maintainer

                    self.fix(output, f'  new `maintainer`: {correct_maintainer}')
                else:
                    self.fail(output)


class NameValidator(ManifestValidator):
    def validate(self, check_name, decoded, fix):
        correct_name = check_name
        name = decoded.get('name')
        if not isinstance(name, str) or name.lower() != correct_name.lower():
            output = f'  incorrect `name`: {name}'
            if fix:
                decoded['name'] = correct_name
                self.fix(output, f'  new `name`: {correct_name}')
            else:
                self.fail(output)


class MetricsMetadataValidator(MaintainerValidator):
    def validate(self, check_name, decoded, fix):
        # metrics_metadata
        metadata_in_manifest = decoded.get('assets', {}).get('metrics_metadata')
        metadata_file_exists = os.path.isfile(get_metadata_file(check_name))
        if not metadata_in_manifest and metadata_file_exists:
            # There is a metadata.csv file but no entry in the manifest.json
            self.fail('  metadata.csv exists but not defined in the manifest.json')
        elif metadata_in_manifest and not metadata_file_exists:
            # There is an entry in the manifest.json file but the referenced csv file does not exist.
            self.fail('  metrics_metadata in manifest.json references a non-existing file.')


class MetricToCheckValidator(MaintainerValidator):
    def validate(self, check_name, decoded, _):
        metadata_in_manifest = decoded.get('assets', {}).get('metrics_metadata')
        # metric_to_check
        metric_to_check = decoded.get('metric_to_check')
        if metric_to_check:
            metrics_to_check = metric_to_check if isinstance(metric_to_check, list) else [metric_to_check]
            for metric in metrics_to_check:
                metric_integration_check_name = check_name
                # snmp vendor specific integrations define metric_to_check
                # with metrics from `snmp` integration
                if check_name.startswith('snmp_') and not metadata_in_manifest:
                    metric_integration_check_name = 'snmp'
                if (
                    not is_metric_in_metadata_file(metric, metric_integration_check_name)
                    and metric not in METRIC_TO_CHECK_WHITELIST
                ):
                    self.fail(f'  metric_to_check not in metadata.csv: {metric!r}')
        elif metadata_in_manifest and check_name != 'snmp' and not (self.is_extras or self.is_marketplace):
            # TODO remove exemptions for integrations-extras and marketplace in future
            # if we have a metadata.csv file but no `metric_to_check` raise an error
            metadata_file = get_metadata_file(check_name)
            if os.path.isfile(metadata_file):
                for _, row in read_metadata_rows(metadata_file):
                    # there are cases of metadata.csv files with just a header but no metrics
                    if row:
                        self.fail('  metric_to_check not included in manifest.json')


class SupportValidator(ManifestValidator):
    def validate(self, check_name, decoded, fix):
        if self.is_extras:
            correct_support = 'contrib'
        elif self.is_marketplace:
            correct_support = 'partner'
        else:
            correct_support = 'core'

        support = decoded.get('support')
        if support != correct_support:
            output = f'  incorrect `support`: {support}'
            if fix:
                decoded['support'] = correct_support
                self.fix(output, f'  new `support`: {correct_support}')
            else:
                self.fail(output)


class IsPublicValidator(ManifestValidator):
    def validate(self, check_name, decoded, fix):
        correct_is_public = True
        is_public = decoded.get('is_public')
        if not isinstance(is_public, bool):
            output = '  required boolean: is_public'

            if fix:
                decoded['is_public'] = correct_is_public
                self.fix(output, f'  new `is_public`: {correct_is_public}')
            else:
                self.fail(output)


class ImmutableAttributesValidator(ManifestValidator):
    """Ensure attributes haven't changed
    Skip if the manifest is a new file (i.e. new integration)
    """

    def validate(self, check_name, decoded, fix):
        manifest_fields_changed = content_changed(file_glob=f"{check_name}/manifest.json")
        if 'new file' not in manifest_fields_changed:
            for field in FIELDS_NOT_ALLOWED_TO_CHANGE:
                if field in manifest_fields_changed:
                    output = f'Attribute `{field}` is not allowed to be modified. Please revert to original value'
                    self.fail(output)
        else:
            self.result.messages['info'].append(
                "  skipping check for changed fields: integration not on default branch"
            )


def get_all_validators(is_extras, is_marketplace):
    return [
        AttributesValidator(),
        GUIDValidator(),
        ManifestVersionValidator(),
        MaintainerValidator(is_extras, is_marketplace),
        NameValidator(),
        MetricsMetadataValidator(),
        MetricToCheckValidator(is_extras, is_marketplace),
        SupportValidator(is_extras, is_marketplace),
        IsPublicValidator(),
        ImmutableAttributesValidator(),
    ]
