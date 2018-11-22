# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import json
import uuid
from collections import OrderedDict

import click
from six import string_types

from ..utils import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning
from ...constants import get_root
from ...utils import parse_version_parts
from ....compat import JSONDecodeError
from ....utils import basepath, file_exists, read_file, write_file

REQUIRED_ATTRIBUTES = {
    'categories',
    'creates_events',
    'display_name',
    'guid',
    'is_public',
    'maintainer',
    'manifest_version',
    'name',
    'public_title',
    'short_description',
    'support',
    'supported_os',
    'type'
}

OPTIONAL_ATTRIBUTES = {
    'aliases',
    'description',
    'is_beta',
    # Move these two below (metric_to_check and metric_prefix) to mandatory when all integration are fixed
    'metric_to_check',
    'metric_prefix',
    'process_signatures',
}

ALL_ATTRIBUTES = REQUIRED_ATTRIBUTES | OPTIONAL_ATTRIBUTES


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate `manifest.json` files'
)
@click.option('--fix', is_flag=True, help='Attempt to fix errors')
@click.option('--include-extras', '-i', is_flag=True, help='Include optional fields')
def manifest(fix, include_extras):
    """Validate `manifest.json` files."""
    all_guids = {}

    root = get_root()
    root_name = basepath(get_root())

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
                decoded = json.loads(read_file(manifest_file).strip(), object_pairs_hook=OrderedDict)
            except JSONDecodeError as e:
                failed_checks += 1
                echo_info("{}/manifest.json... ".format(check_name), nl=False)
                echo_failure("FAILED")
                echo_failure('  invalid json: {}'.format(e))
                continue

            # attributes are valid
            attrs = set(decoded)
            for attr in sorted(attrs - ALL_ATTRIBUTES):
                file_failures += 1
                display_queue.append((echo_failure, '  Attribute `{}` is invalid'.format(attr)))
            for attr in sorted(REQUIRED_ATTRIBUTES - attrs):
                file_failures += 1
                display_queue.append((echo_failure, '  Attribute `{}` is required'.format(attr)))

            # guid
            guid = decoded.get('guid')
            if guid in all_guids:
                file_failures += 1
                output = '  duplicate `guid`: `{}` from `{}`'.format(guid, all_guids[guid])
                if fix:
                    new_guid = uuid.uuid4()
                    all_guids[new_guid] = check_name
                    decoded['guid'] = new_guid

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, '  new `guid`: {}'.format(new_guid)))

                    file_failures -= 1
                    file_fixed = True
                else:
                    display_queue.append((echo_failure, output))
            elif not guid or not isinstance(guid, string_types):
                file_failures += 1
                output = '  required non-null string: guid'
                if fix:
                    new_guid = uuid.uuid4()
                    all_guids[new_guid] = check_name
                    decoded['guid'] = new_guid

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, '  new `guid`: {}'.format(new_guid)))

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
                    output = '  invalid `manifest_version`: {}'.format(manifest_version)

                if fix:
                    version_parts = parse_version_parts(correct_manifest_version)
                    decoded['manifest_version'] = correct_manifest_version

                    display_queue.append((echo_warning, output))
                    display_queue.append((
                        echo_success, '  new `manifest_version`: {}'.format(correct_manifest_version)
                    ))

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
                    output = '  outdated `manifest_version`: {}'.format(manifest_version)

                    if fix:
                        decoded['manifest_version'] = correct_manifest_version

                        display_queue.append((echo_warning, output))
                        display_queue.append((
                            echo_success, '  new `manifest_version`: {}'.format(correct_manifest_version)
                        ))

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
                            display_queue.append((echo_failure, '  invalid `version`: {}'.format(version)))

            # maintainer
            correct_maintainer = 'help@datadoghq.com'
            maintainer = decoded.get('maintainer')
            if maintainer != correct_maintainer:
                file_failures += 1
                output = '  incorrect `maintainer`: {}'.format(maintainer)

                if fix:
                    decoded['maintainer'] = correct_maintainer

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, '  new `maintainer`: {}'.format(correct_maintainer)))

                    file_failures -= 1
                    file_fixed = True
                else:
                    display_queue.append((echo_failure, output))

            # name
            correct_name = check_name
            name = decoded.get('name')
            if not isinstance(name, string_types) or name.lower() != correct_name.lower():
                file_failures += 1
                output = '  incorrect `name`: {}'.format(name)

                if fix:
                    decoded['name'] = correct_name

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, '  new `name`: {}'.format(correct_name)))

                    file_failures -= 1
                    file_fixed = True
                else:
                    display_queue.append((echo_failure, output))

            # short_description
            short_description = decoded.get('short_description')
            if not short_description or not isinstance(short_description, string_types):
                file_failures += 1
                display_queue.append((echo_failure, '  required non-null string: short_description'))
            if len(short_description) > 80:
                file_failures += 1
                display_queue.append((echo_failure, '  should contain 80 characters maximum: short_description'))

            # support
            correct_support = 'contrib' if root_name == 'extras' else 'core'
            support = decoded.get('support')
            if support != correct_support:
                file_failures += 1
                output = '  incorrect `support`: {}'.format(support)

                if fix:
                    decoded['support'] = correct_support

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, '  new `support`: {}'.format(correct_support)))

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
                        display_queue.append((
                            echo_failure, '  unknown `supported_os`: {}'.format(', '.join(unknown_systems))
                        ))

                # public_title
                public_title = decoded.get('public_title')
                if not public_title or not isinstance(public_title, string_types):
                    file_failures += 1
                    display_queue.append((echo_failure, '  required non-null string: public_title'))
                else:
                    title_start = 'Datadog-'
                    title_end = ' Integration'
                    section_char_set = set(public_title[len(title_start):-len(title_end)].lower())
                    check_name_char_set = set(check_name.lower())
                    character_overlap = check_name_char_set & section_char_set

                    correct_start = public_title.startswith(title_start)
                    correct_end = public_title.endswith(title_end)
                    overlap_enough = len(character_overlap) > int(len(check_name_char_set) * 0.5)

                    if not (correct_start and correct_end and overlap_enough):
                        file_failures += 1
                        display_queue.append((echo_failure, '  invalid `public_title`: {}'.format(public_title)))

                # categories
                categories = decoded.get('categories')
                if not categories or not isinstance(categories, list):
                    file_failures += 1
                    display_queue.append((echo_failure, '  required non-null sequence: categories'))

                # type
                correct_integration_type = 'check'
                integration_type = decoded.get('type')
                if not integration_type or not isinstance(integration_type, string_types):
                    file_failures += 1
                    output = '  required non-null string: type'

                    if fix:
                        decoded['type'] = correct_integration_type

                        display_queue.append((echo_warning, output))
                        display_queue.append((echo_success, '  new `type`: {}'.format(correct_integration_type)))

                        file_failures -= 1
                        file_fixed = True
                    else:
                        display_queue.append((echo_failure, output))
                elif integration_type != correct_integration_type:
                    file_failures += 1
                    output = '  invalid `type`: {}'.format(integration_type)

                    if fix:
                        decoded['type'] = correct_integration_type

                        display_queue.append((echo_warning, output))
                        display_queue.append((echo_success, '  new `type`: {}'.format(correct_integration_type)))

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
                        display_queue.append((echo_success, '  new `is_public`: {}'.format(correct_is_public)))

                        file_failures -= 1
                        file_fixed = True
                    else:
                        display_queue.append((echo_failure, output))

            if file_failures > 0:
                failed_checks += 1
                # Display detailed info if file invalid
                echo_info("{}/manifest.json... ".format(check_name), nl=False)
                echo_failure("FAILED")
                for display_func, message in display_queue:
                    display_func(message)
            elif not file_fixed:
                ok_checks += 1

            if fix and file_fixed:
                new_manifest = '{}\n'.format(json.dumps(decoded, indent=2, separators=(',', ': ')))
                write_file(manifest_file, new_manifest)
                # Display detailed info if file has been completely fixed
                if file_failures == 0:
                    fixed_checks += 1
                    echo_info("{}/manifest.json... ".format(check_name), nl=False)
                    echo_success("FIXED")
                    for display_func, message in display_queue:
                        display_func(message)

    if ok_checks:
        echo_success("{} valid files".format(ok_checks))
    if fixed_checks:
        echo_info("{} fixed files".format(fixed_checks))
    if failed_checks:
        echo_failure("{} invalid files".format(failed_checks))
        abort()
