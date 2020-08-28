# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import uuid

import click
import jsonschema
import requests

from ....utils import file_exists, read_file, write_file
from ...constants import get_root
from ...utils import get_metadata_file, parse_version_parts, read_metadata_rows
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning

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
    for _, row in read_metadata_rows(metadata_file):
        if row['metric_name'] == metric:
            return True
    return False


def get_original_manifest_field(check_name, field_to_check, repo_url, manifests_from_master):
    repo_url = f'{repo_url}/{check_name}/manifest.json'
    if manifests_from_master.get(check_name):
        data = manifests_from_master.get(check_name)
    else:
        data = requests.get(repo_url.format(check_name))
        manifests_from_master[check_name] = data

    if data.status_code == 404:
        # This integration isn't on the provided repo yet, so it's field can change
        return None

    data.raise_for_status()
    decoded_master = data.json()
    return decoded_master.get(field_to_check)


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate `manifest.json` files')
@click.option('--fix', is_flag=True, help='Attempt to fix errors')
@click.option('--include-extras', '-i', is_flag=True, help='Include optional fields, and extra validations')
@click.option(
    '--repo_url', '-r', help='The raw github URL to the base of the repository to compare manifest fields against'
)
@click.pass_context
def manifest(ctx, fix, include_extras, repo_url):
    """Validate `manifest.json` files."""
    all_guids = {}
    raw_gh_url = 'https://raw.githubusercontent.com/DataDog/{}/master/'

    root = get_root()
    is_extras = ctx.obj['repo_choice'] == 'extras'
    is_marketplace = ctx.obj['repo_choice'] == 'marketplace'
    formatted_repo_url = repo_url or raw_gh_url.format(os.path.basename(root))
    ok_checks = 0
    failed_checks = 0
    fixed_checks = 0
    manifests_from_master = {}

    echo_info("Validating all manifest.json files...")
    for check_name in sorted(os.listdir(root)):
        manifest_file = os.path.join(root, check_name, 'manifest.json')

        if file_exists(manifest_file):
            display_queue = []
            file_failures = 0
            file_fixed = False

            try:
                decoded = json.loads(read_file(manifest_file).strip())
            except json.JSONDecodeError as e:
                failed_checks += 1
                echo_info(f"{check_name}/manifest.json... ", nl=False)
                echo_failure("FAILED")
                echo_failure(f'  invalid json: {e}')
                continue

            # attributes are valid
            errors = sorted(get_manifest_schema().iter_errors(decoded), key=lambda e: e.path)
            if errors:
                file_failures += 1
                for error in errors:
                    display_queue.append((echo_failure, f'  {error.message}'))

            # guid
            guid = decoded.get('guid')
            if guid in all_guids:
                file_failures += 1
                output = f'  duplicate `guid`: `{guid}` from `{all_guids[guid]}`'
                if fix:
                    new_guid = uuid.uuid4()
                    all_guids[new_guid] = check_name
                    decoded['guid'] = new_guid

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, f'  new `guid`: {new_guid}'))

                    file_failures -= 1
                    file_fixed = True
                else:
                    display_queue.append((echo_failure, output))
            elif not guid or not isinstance(guid, str):
                file_failures += 1
                output = '  required non-null string: guid'
                if fix:
                    new_guid = uuid.uuid4()
                    all_guids[new_guid] = check_name
                    decoded['guid'] = new_guid

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, f'  new `guid`: {new_guid}'))

                    file_failures -= 1
                    file_fixed = True
                else:
                    display_queue.append((echo_failure, output))
            else:
                all_guids[guid] = check_name

            # manifest_version
            correct_manifest_version = '1.0.0'
            manifest_version = decoded.get('manifest_version')
            version_parts = parse_version_parts(manifest_version)
            if len(version_parts) != 3:
                file_failures += 1

                if not manifest_version:
                    output = '  required non-null string: manifest_version'
                else:
                    output = f'  invalid `manifest_version`: {manifest_version}'

                if fix:
                    version_parts = parse_version_parts(correct_manifest_version)
                    decoded['manifest_version'] = correct_manifest_version

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, f'  new `manifest_version`: {correct_manifest_version}'))

                    file_failures -= 1
                    file_fixed = True
                else:
                    display_queue.append((echo_failure, output))

            if len(version_parts) == 3:
                about_exists = os.path.isfile(
                    os.path.join(root, check_name, 'datadog_checks', check_name, '__about__.py')
                )
                if version_parts >= [1, 0, 0]:
                    if 'version' in decoded and about_exists:
                        file_failures += 1
                        output = '  outdated field: version'

                        if fix:
                            del decoded['version']

                            display_queue.append((echo_warning, output))
                            display_queue.append((echo_success, '  removed field: version'))

                            file_failures -= 1
                            file_fixed = True
                        else:
                            display_queue.append((echo_failure, output))

                elif about_exists:
                    file_failures += 1
                    output = f'  outdated `manifest_version`: {manifest_version}'

                    if fix:
                        decoded['manifest_version'] = correct_manifest_version

                        display_queue.append((echo_warning, output))
                        display_queue.append((echo_success, f'  new `manifest_version`: {correct_manifest_version}'))

                        if 'version' in decoded:
                            del decoded['version']
                            display_queue.append((echo_success, '  removed field: version'))

                        file_failures -= 1
                        file_fixed = True
                    else:
                        display_queue.append((echo_failure, output))
                else:
                    version = decoded.get('version')
                    version_parts = parse_version_parts(version)
                    if len(version_parts) != 3:
                        file_failures += 1

                        if not version:
                            display_queue.append((echo_failure, '  required non-null string: version'))
                        else:
                            display_queue.append((echo_failure, f'  invalid `version`: {version}'))

            # maintainer
            if not is_extras and not is_marketplace:
                correct_maintainer = 'help@datadoghq.com'
                maintainer = decoded.get('maintainer')
                if maintainer != correct_maintainer:
                    file_failures += 1
                    output = f'  incorrect `maintainer`: {maintainer}'

                    if fix:
                        decoded['maintainer'] = correct_maintainer

                        display_queue.append((echo_warning, output))
                        display_queue.append((echo_success, f'  new `maintainer`: {correct_maintainer}'))

                        file_failures -= 1
                        file_fixed = True
                    else:
                        display_queue.append((echo_failure, output))

            # name
            correct_name = check_name
            name = decoded.get('name')
            if not isinstance(name, str) or name.lower() != correct_name.lower():
                file_failures += 1
                output = f'  incorrect `name`: {name}'

                if fix:
                    decoded['name'] = correct_name

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, f'  new `name`: {correct_name}'))

                    file_failures -= 1
                    file_fixed = True
                else:
                    display_queue.append((echo_failure, output))

            # metric_to_check
            metric_to_check = decoded.get('metric_to_check')
            if metric_to_check:
                metrics_to_check = metric_to_check if isinstance(metric_to_check, list) else [metric_to_check]
                for metric in metrics_to_check:
                    if not is_metric_in_metadata_file(metric, check_name) and metric not in METRIC_TO_CHECK_WHITELIST:
                        file_failures += 1
                        display_queue.append((echo_failure, f'  metric_to_check not in metadata.csv: {metric!r}'))

            # support
            if is_extras:
                correct_support = 'contrib'
            elif is_marketplace:
                correct_support = 'partner'
            else:
                correct_support = 'core'

            support = decoded.get('support')
            if support != correct_support:
                file_failures += 1
                output = f'  incorrect `support`: {support}'

                if fix:
                    decoded['support'] = correct_support

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, f'  new `support`: {correct_support}'))

                    file_failures -= 1
                    file_fixed = True
                else:
                    display_queue.append((echo_failure, output))

            if include_extras:
                # Ensure attributes haven't changed
                for field in FIELDS_NOT_ALLOWED_TO_CHANGE:
                    original_value = get_original_manifest_field(
                        check_name, field, formatted_repo_url, manifests_from_master
                    )
                    output = f'Attribute `{field}` is not allowed to be modified.'
                    if original_value and original_value != decoded.get(field):
                        file_failures += 1
                        if fix:
                            decoded[field] = original_value
                            file_failures -= 1
                            file_fixed = True
                            display_queue.append((echo_warning, output))
                            display_queue.append((echo_success, f'  original {field}: {original_value}'))
                        else:
                            output += f" Please use the existing value: {original_value}"
                            display_queue.append((echo_failure, output))
                    elif not original_value:
                        output = f"  No existing field on default branch: {field}"
                        display_queue.append((echo_warning, output))

                # is_public
                correct_is_public = True
                is_public = decoded.get('is_public')
                if not isinstance(is_public, bool):
                    file_failures += 1
                    output = '  required boolean: is_public'

                    if fix:
                        decoded['is_public'] = correct_is_public

                        display_queue.append((echo_warning, output))
                        display_queue.append((echo_success, f'  new `is_public`: {correct_is_public}'))

                        file_failures -= 1
                        file_fixed = True
                    else:
                        display_queue.append((echo_failure, output))

            if file_failures > 0:
                failed_checks += 1
                # Display detailed info if file invalid
                echo_info(f"{check_name}/manifest.json... ", nl=False)
                echo_failure("FAILED")
                for display_func, message in display_queue:
                    display_func(message)
            elif not file_fixed:
                ok_checks += 1

            if fix and file_fixed:
                new_manifest = f"{json.dumps(decoded, indent=2, separators=(',', ': '))}\n"
                write_file(manifest_file, new_manifest)
                # Display detailed info if file has been completely fixed
                if file_failures == 0:
                    fixed_checks += 1
                    echo_info(f"{check_name}/manifest.json... ", nl=False)
                    echo_success("FIXED")
                    for display_func, message in display_queue:
                        display_func(message)

    if ok_checks:
        echo_success(f"{ok_checks} valid files")
    if fixed_checks:
        echo_info(f"{fixed_checks} fixed files")
    if failed_checks:
        echo_failure(f"{failed_checks} invalid files")
        abort()
