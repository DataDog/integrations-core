# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import uuid

import click

from datadog_checks.dev.tooling.manifest_validator.schema import get_manifest_schema

from ....fs import file_exists, read_file, write_file
from ...constants import get_root
from ...git import content_changed
from ...utils import get_metadata_file, is_metric_in_metadata_file, parse_version_parts, read_metadata_rows
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning

FIELDS_NOT_ALLOWED_TO_CHANGE = ["integration_id", "display_name", "guid"]

METRIC_TO_CHECK_EXCLUDE_LIST = {
    'openstack.controller',  # "Artificial" metric, shouldn't be listed in metadata file.
    'riakcs.bucket_list_pool.workers',  # RiakCS 2.1 metric, but metadata.csv lists RiakCS 2.0 metrics only.
}


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate `manifest.json` files')
@click.option('--fix', is_flag=True, help='Attempt to fix errors')
@click.pass_context
def manifest(ctx, fix):
    """Validate `manifest.json` files."""
    all_guids = {}

    root = get_root()
    is_extras = ctx.obj['repo_choice'] == 'extras'
    is_marketplace = ctx.obj['repo_choice'] == 'marketplace'
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
            errors = sorted(get_manifest_schema().iter_errors(decoded), key=lambda e: e.path)
            if errors:
                file_failures += 1
                for error in errors:
                    display_queue.append(
                        (echo_failure, f'  {"->".join(map(str, error.absolute_path))} Error: {error.message}')
                    )

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
                if not maintainer.isascii():
                    display_queue.append((echo_failure, f'  `maintainer` contains non-ascii character: {maintainer}'))
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

            # metrics_metadata
            metadata_in_manifest = decoded.get('assets', {}).get('metrics_metadata')
            metadata_file_exists = os.path.isfile(get_metadata_file(check_name))
            if not metadata_in_manifest and metadata_file_exists:
                # There is a metadata.csv file but no entry in the manifest.json
                file_failures += 1
                display_queue.append((echo_failure, '  metadata.csv exists but not defined in the manifest.json'))
            elif metadata_in_manifest and not metadata_file_exists:
                # There is an entry in the manifest.json file but the referenced csv file does not exist.
                file_failures += 1
                display_queue.append(
                    (echo_failure, '  metrics_metadata in manifest.json references a non-existing file.')
                )

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
                        and metric not in METRIC_TO_CHECK_EXCLUDE_LIST
                    ):
                        file_failures += 1
                        display_queue.append((echo_failure, f'  metric_to_check not in metadata.csv: {metric!r}'))
            elif metadata_in_manifest and check_name != 'snmp' and check_name != 'moogsoft':
                # TODO: Remove moogsoft exception once https://github.com/DataDog/marketplace/pull/116 is merged
                # if we have a metadata.csv file but no `metric_to_check` raise an error
                metadata_file = get_metadata_file(check_name)
                if os.path.isfile(metadata_file):
                    for _, row in read_metadata_rows(metadata_file):
                        # there are cases of metadata.csv files with just a header but no metrics
                        if row:
                            file_failures += 1
                            display_queue.append((echo_failure, '  metric_to_check not included in manifest.json'))
                            break

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

            # Ensure attributes haven't changed
            # Skip if the manifest is a new file (i.e. new integration)
            manifest_fields_changed = content_changed(file_glob=f"{check_name}/manifest.json")
            if 'new file' not in manifest_fields_changed:
                for field in FIELDS_NOT_ALLOWED_TO_CHANGE:
                    if field in manifest_fields_changed:
                        output = f'Attribute `{field}` is not allowed to be modified. Please revert to original value'
                        file_failures += 1
                        display_queue.append((echo_failure, output))
            else:
                display_queue.append(
                    (echo_info, "  skipping check for changed fields: integration not on default branch")
                )

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
