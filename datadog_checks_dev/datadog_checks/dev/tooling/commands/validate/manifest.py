# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import re
import uuid

import click

from ....utils import file_exists, read_file, write_file
from ...constants import get_root
from ...utils import get_metadata_file, parse_version_parts, read_metadata_rows
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning

REQUIRED_ATTRIBUTES = {
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
}

REQUIRED_ASSET_ATTRIBUTES = {'monitors', 'dashboards', 'service_checks'}

OPTIONAL_ATTRIBUTES = {
    'aliases',
    'description',
    'is_beta',
    # Move these two below (metric_to_check, metric_prefix)
    # to mandatory when all integration are fixed
    'metric_to_check',
    'metric_prefix',
    'process_signatures',
}

METRIC_TO_CHECK_WHITELIST = {
    'openstack.controller',  # "Artificial" metric, shouldn't be listed in metadata file.
    'riakcs.bucket_list_pool.workers',  # RiakCS 2.1 metric, but metadata.csv lists RiakCS 2.0 metrics only.
}

ALL_ATTRIBUTES = REQUIRED_ATTRIBUTES | OPTIONAL_ATTRIBUTES

INTEGRATION_ID_REGEX = r'^[a-z][a-z0-9-]{0,254}(?<!-)$'


def is_metric_in_metadata_file(metric, check):
    """
    Return True if `metric` is listed in the check's `metadata.csv` file, False otherwise.
    """
    metadata_file = get_metadata_file(check)
    for _, row in read_metadata_rows(metadata_file):
        if row['metric_name'] == metric:
            return True
    return False


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate `manifest.json` files')
@click.option('--fix', is_flag=True, help='Attempt to fix errors')
@click.option('--include-extras', '-i', is_flag=True, help='Include optional fields')
@click.pass_context
def manifest(ctx, fix, include_extras):
    """Validate `manifest.json` files."""
    all_guids = {}

    root = get_root()
    is_extras = ctx.obj['repo_choice'] == 'extras'

    ok_checks = 0
    failed_checks = 0
    fixed_checks = 0
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
            attrs = set(decoded)
            for attr in sorted(attrs - ALL_ATTRIBUTES):
                file_failures += 1
                display_queue.append((echo_failure, f'  Attribute `{attr}` is invalid'))
            for attr in sorted(REQUIRED_ATTRIBUTES - attrs):
                file_failures += 1
                display_queue.append((echo_failure, f'  Attribute `{attr}` is required'))
            for attr in sorted(REQUIRED_ASSET_ATTRIBUTES - set(decoded.get('assets', {}))):
                file_failures += 1
                display_queue.append((echo_failure, f' Attribute `{attr}` under `assets` is required'))

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

            # integration_id
            integration_id = decoded.get('integration_id')
            if not re.search(INTEGRATION_ID_REGEX, integration_id):
                file_failures += 1
                output = 'integration_id contains invalid characters'
                display_queue.append((echo_failure, output))

            # maintainer
            if not is_extras:
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

            # short_description
            short_description = decoded.get('short_description')
            if not short_description or not isinstance(short_description, str):
                file_failures += 1
                display_queue.append((echo_failure, '  required non-null string: short_description'))
            if len(short_description) > 80:
                file_failures += 1
                display_queue.append((echo_failure, '  should contain 80 characters maximum: short_description'))

            # metric_to_check
            metric_to_check = decoded.get('metric_to_check')
            if metric_to_check:
                metrics_to_check = metric_to_check if isinstance(metric_to_check, list) else [metric_to_check]
                for metric in metrics_to_check:
                    if not is_metric_in_metadata_file(metric, check_name) and metric not in METRIC_TO_CHECK_WHITELIST:
                        file_failures += 1
                        display_queue.append((echo_failure, f'  metric_to_check not in metadata.csv: {metric!r}'))

            # support
            correct_support = 'contrib' if is_extras else 'core'
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
                # supported_os
                supported_os = decoded.get('supported_os')
                if not supported_os or not isinstance(supported_os, list):
                    file_failures += 1
                    display_queue.append((echo_failure, '  required non-null sequence: supported_os'))
                else:
                    known_systems = {'linux', 'mac_os', 'windows'}
                    unknown_systems = sorted(set(supported_os) - known_systems)
                    if unknown_systems:
                        file_failures += 1
                        display_queue.append((echo_failure, f"  unknown `supported_os`: {', '.join(unknown_systems)}"))

                # public_title
                public_title = decoded.get('public_title')
                if not public_title or not isinstance(public_title, str):
                    file_failures += 1
                    display_queue.append((echo_failure, '  required non-null string: public_title'))
                else:
                    title_start = 'Datadog-'
                    title_end = ' Integration'
                    section_char_set = set(public_title[len(title_start) : -len(title_end)].lower())
                    check_name_char_set = set(check_name.lower())
                    character_overlap = check_name_char_set & section_char_set

                    correct_start = public_title.startswith(title_start)
                    correct_end = public_title.endswith(title_end)
                    overlap_enough = len(character_overlap) > int(len(check_name_char_set) * 0.5)

                    if not (correct_start and correct_end and overlap_enough):
                        file_failures += 1
                        display_queue.append((echo_failure, f'  invalid `public_title`: {public_title}'))

                # categories
                categories = decoded.get('categories')
                if not categories or not isinstance(categories, list):
                    file_failures += 1
                    display_queue.append((echo_failure, '  required non-null sequence: categories'))

                # type
                correct_integration_types = ['check', 'crawler']
                integration_type = decoded.get('type')
                if not integration_type or not isinstance(integration_type, str):
                    file_failures += 1
                    output = '  required non-null string: type'
                    display_queue.append((echo_failure, output))
                elif integration_type not in correct_integration_types:
                    file_failures += 1
                    output = f'  invalid `type`: {integration_type}'
                    display_queue.append((echo_failure, output))

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
