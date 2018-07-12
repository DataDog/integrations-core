# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import json
import uuid
from collections import OrderedDict

import click
from six import string_types

from .utils import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning
from ..constants import get_root
from ...compat import JSONDecodeError
from ...utils import basepath, file_exists, read_file, write_file


def parse_version_parts(version):
    return (
        [int(v) for v in version.split('.') if v.isdigit()]
        if isinstance(version, string_types) else []
    )


@click.group(
    context_settings=CONTEXT_SETTINGS,
    short_help='Manage manifest files'
)
def manifest():
    pass


@manifest.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate all `manifest.json` files'
)
@click.option('--fix', is_flag=True, help='Attempt to fix errors')
@click.option('--include-extras', '-i', is_flag=True, help='Include optional fields')
def verify(fix, include_extras):
    """Validate all `manifest.json` files."""
    all_guids = {}
    failed = 0

    root = get_root()
    root_name = basepath(get_root())

    for check_name in sorted(os.listdir(root)):
        manifest_file = os.path.join(root, check_name, 'manifest.json')

        if file_exists(manifest_file):
            display_queue = [(echo_info, '{} ->'.format(check_name))]

            try:
                decoded = json.loads(read_file(manifest_file).strip(), object_pairs_hook=OrderedDict)
            except JSONDecodeError:
                failed += 1
                display_queue.append((echo_failure, '  invalid json: {}'.format(manifest_file)))

                for display, message in display_queue:
                    display(message)
                continue

            # guid
            guid = decoded.get('guid')
            if guid in all_guids:
                failed += 1
                output = '  duplicate `guid`: `{}` from `{}`'.format(guid, all_guids[guid])
                if fix:
                    new_guid = uuid.uuid4()
                    all_guids[new_guid] = check_name
                    decoded['guid'] = new_guid

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, '  new `guid`: {}'.format(new_guid)))

                    failed -= 1
                else:
                    display_queue.append((echo_failure, output))
            elif not guid or not isinstance(guid, string_types):
                failed += 1
                output = '  required non-null string: guid'
                if fix:
                    new_guid = uuid.uuid4()
                    all_guids[new_guid] = check_name
                    decoded['guid'] = new_guid

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, '  new `guid`: {}'.format(new_guid)))

                    failed -= 1
                else:
                    display_queue.append((echo_failure, output))
            else:
                all_guids[guid] = check_name

            # manifest_version
            correct_manifest_version = '1.0.0'
            manifest_version = decoded.get('manifest_version')
            version_parts = parse_version_parts(manifest_version)
            if len(version_parts) != 3:
                failed += 1

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

                    failed -= 1
                else:
                    display_queue.append((echo_failure, output))

            if len(version_parts) == 3:
                about_exists = os.path.isfile(
                    os.path.join(root, check_name, 'datadog_checks', check_name, '__about__.py')
                )
                if version_parts >= [1, 0, 0]:
                    if 'version' in decoded and about_exists:
                        failed += 1
                        output = '  outdated field: version'

                        if fix:
                            del decoded['version']

                            display_queue.append((echo_warning, output))
                            display_queue.append((echo_success, '  removed field: version'))

                            failed -= 1
                        else:
                            display_queue.append((echo_failure, output))

                    if 'max_agent_version' in decoded:
                        failed += 1
                        output = '  outdated field: max_agent_version'

                        if fix:
                            del decoded['max_agent_version']

                            display_queue.append((echo_warning, output))
                            display_queue.append((echo_success, '  removed field: max_agent_version'))

                            failed -= 1
                        else:
                            display_queue.append((echo_failure, output))

                    if 'min_agent_version' in decoded:
                        failed += 1
                        output = '  outdated field: min_agent_version'

                        if fix:
                            del decoded['min_agent_version']

                            display_queue.append((echo_warning, output))
                            display_queue.append((echo_success, '  removed field: min_agent_version'))

                            failed -= 1
                        else:
                            display_queue.append((echo_failure, output))
                elif about_exists:
                    failed += 1
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

                        if 'max_agent_version' in decoded:
                            del decoded['max_agent_version']
                            display_queue.append((echo_success, '  removed field: max_agent_version'))

                        if 'min_agent_version' in decoded:
                            del decoded['min_agent_version']
                            display_queue.append((echo_success, '  removed field: min_agent_version'))

                        failed -= 1
                    else:
                        display_queue.append((echo_failure, output))
                else:
                    version = decoded.get('version')
                    version_parts = parse_version_parts(version)
                    if len(version_parts) != 3:
                        failed += 1

                        if not version:
                            display_queue.append((echo_failure, '  required non-null string: version'))
                        else:
                            display_queue.append((echo_failure, '  invalid `version`: {}'.format(version)))

            # maintainer
            correct_maintainer = 'help@datadoghq.com'
            maintainer = decoded.get('maintainer')
            if maintainer != correct_maintainer:
                failed += 1
                output = '  incorrect `maintainer`: {}'.format(maintainer)

                if fix:
                    decoded['maintainer'] = correct_maintainer

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, '  new `maintainer`: {}'.format(correct_maintainer)))

                    failed -= 1
                else:
                    display_queue.append((echo_failure, output))

            # name
            correct_name = check_name
            name = decoded.get('name')
            if not isinstance(name, string_types) or name.lower() != correct_name.lower():
                failed += 1
                output = '  incorrect `name`: {}'.format(name)

                if fix:
                    decoded['name'] = correct_name

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, '  new `name`: {}'.format(correct_name)))

                    failed -= 1
                else:
                    display_queue.append((echo_failure, output))

            # short_description
            short_description = decoded.get('short_description')
            if not short_description or not isinstance(short_description, string_types):
                failed += 1
                display_queue.append((echo_failure, '  required non-null string: short_description'))

            # support
            correct_support = 'contrib' if root_name == 'extras' else 'core'
            support = decoded.get('support')
            if support != correct_support:
                failed += 1
                output = '  incorrect `support`: {}'.format(support)

                if fix:
                    decoded['support'] = correct_support

                    display_queue.append((echo_warning, output))
                    display_queue.append((echo_success, '  new `support`: {}'.format(correct_support)))

                    failed -= 1
                else:
                    display_queue.append((echo_failure, output))

            if include_extras:
                # supported_os
                supported_os = decoded.get('supported_os')
                if not supported_os or not isinstance(supported_os, list):
                    failed += 1
                    display_queue.append((echo_failure, '  required non-null sequence: supported_os'))
                else:
                    known_systems = {'linux', 'mac_os', 'windows'}
                    unknown_systems = sorted(set(supported_os) - known_systems)
                    if unknown_systems:
                        failed += 1
                        display_queue.append((
                            echo_failure, '  unknown `supported_os`: {}'.format(', '.join(unknown_systems))
                        ))

                # public_title
                public_title = decoded.get('public_title')
                if not public_title or not isinstance(public_title, string_types):
                    failed += 1
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
                        failed += 1
                        display_queue.append((echo_failure, '  invalid `public_title`: {}'.format(public_title)))

                # categories
                categories = decoded.get('categories')
                if not categories or not isinstance(categories, list):
                    failed += 1
                    display_queue.append((echo_failure, '  required non-null sequence: categories'))

                # type
                correct_integration_type = 'check'
                integration_type = decoded.get('type')
                if not integration_type or not isinstance(integration_type, string_types):
                    failed += 1
                    output = '  required non-null string: type'

                    if fix:
                        decoded['type'] = correct_integration_type

                        display_queue.append((echo_warning, output))
                        display_queue.append((echo_success, '  new `type`: {}'.format(correct_integration_type)))

                        failed -= 1
                    else:
                        display_queue.append((echo_failure, output))
                elif integration_type != correct_integration_type:
                    failed += 1
                    output = '  invalid `type`: {}'.format(integration_type)

                    if fix:
                        decoded['type'] = correct_integration_type

                        display_queue.append((echo_warning, output))
                        display_queue.append((echo_success, '  new `type`: {}'.format(correct_integration_type)))

                        failed -= 1
                    else:
                        display_queue.append((echo_failure, output))

                # is_public
                correct_is_public = True
                is_public = decoded.get('is_public')
                if not isinstance(is_public, bool):
                    failed += 1
                    output = '  required boolean: is_public'

                    if fix:
                        decoded['is_public'] = correct_is_public

                        display_queue.append((echo_warning, output))
                        display_queue.append((echo_success, '  new `is_public`: {}'.format(correct_is_public)))

                        failed -= 1
                    else:
                        display_queue.append((echo_failure, output))
                elif is_public != correct_is_public:
                    failed += 1
                    output = '  invalid `is_public`: {}'.format(is_public)

                    if fix:
                        decoded['is_public'] = correct_is_public

                        display_queue.append((echo_warning, output))
                        display_queue.append((echo_success, '  new `is_public`: {}'.format(correct_is_public)))

                        failed -= 1
                    else:
                        display_queue.append((echo_failure, output))

                # has_logo
                default_has_logo = True
                has_logo = decoded.get('has_logo')
                if not isinstance(has_logo, bool):
                    failed += 1
                    output = '  required boolean: has_logo'

                    if fix:
                        decoded['has_logo'] = default_has_logo

                        display_queue.append((echo_warning, output))
                        display_queue.append((echo_success, '  new `has_logo`: {}'.format(default_has_logo)))

                        failed -= 1
                    else:
                        display_queue.append((echo_failure, output))

                # doc_link
                doc_link = decoded.get('doc_link')
                if not doc_link or not isinstance(doc_link, string_types):
                    failed += 1
                    display_queue.append((echo_failure, '  required non-null string: doc_link'))
                elif not doc_link.startswith('https://docs.datadoghq.com/integrations/'):
                    failed += 1
                    display_queue.append((echo_failure, '  invalid `doc_link`: {}'.format(doc_link)))

            # See if anything happened
            if len(display_queue) > 1:
                for display, message in display_queue:
                    display(message)

                if fix:
                    new_manifest = '{}\n'.format(json.dumps(decoded, indent=2, separators=(',', ': ')))
                    write_file(manifest_file, new_manifest)

    if failed > 0:
        abort()


@manifest.command(
    'set',
    context_settings=CONTEXT_SETTINGS,
    short_help='Assign values to manifest file entries for every check'
)
@click.argument('key')
@click.argument('value')
def set_value(key, value):
    """Assigns values to manifest file entries for every check."""
    root = get_root()
    updated_checks = 0

    for check in sorted(os.listdir(root)):
        manifest_file = os.path.join(root, check, 'manifest.json')

        if file_exists(manifest_file):
            try:
                decoded = json.loads(read_file(manifest_file).strip(), object_pairs_hook=OrderedDict)
            except JSONDecodeError:
                echo_failure('Invalid json: {}'.format(manifest_file))
                continue

            decoded[key] = value

            new_manifest = '{}\n'.format(
                json.dumps(decoded, indent=2, separators=(',', ': '))
            )

            write_file(manifest_file, new_manifest)

            updated_checks += 1

    display = echo_success if updated_checks else echo_warning
    display('Set `{}` to `{}` in {} checks.'.format(key, value, updated_checks))
