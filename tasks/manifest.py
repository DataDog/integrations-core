# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals

import os
import json
import uuid
from collections import OrderedDict

from invoke import task
from invoke.exceptions import Exit
from six import text_type

from .constants import ROOT


def parse_version_parts(version):
    return (
        [int(v) for v in version.split('.') if v.isdigit()]
        if isinstance(version, text_type) else []
    )


@task(help={
    'update': 'Update every `manifest_version`',
    'fix': 'Attempt making manifests valid',
    'include_extras': 'Include optional fields',
})
def manifest(ctx, update=None, fix=False, include_extras=False):
    """Validate all `manifest.json` files.

    Example invocation:
        inv manifest --update manifest_version=1.0.0
    """
    if update:
        try:
            key, value = update.split('=')
        except ValueError:
            raise Exit('Unable to parse `{}`'.format(update))
    else:
        key, value = None, None

    all_guids = {}
    failed = 0
    output = ''

    for check_name in sorted(os.listdir(ROOT)):
        check_dir = os.path.join(ROOT, check_name)
        manifest_file = os.path.join(check_dir, 'manifest.json')

        if os.path.isfile(manifest_file):
            check_output = '{} ->\n'.format(check_name)

            try:
                with open(manifest_file, 'r') as f:
                    decoded = json.loads(f.read().strip(), object_pairs_hook=OrderedDict)
            except json.JSONDecodeError:
                check_output += '  invalid json: {}\n'.format(manifest_file)
                output += check_output
                failed += 1
                continue

            if update:
                decoded[key] = value
                check_output += '  new `{}`: {}\n'.format(key, value)
            else:
                # guid
                guid = decoded.get('guid')
                if guid in all_guids:
                    check_output += '  duplicate `guid`: `{}` from `{}`\n'.format(guid, all_guids[guid])
                    failed += 1
                    if fix:
                        new_guid = uuid.uuid4()
                        all_guids[new_guid] = check_name
                        decoded['guid'] = new_guid
                        check_output += '  new `guid`: {}\n'.format(new_guid)
                        failed -= 1
                elif not guid or not isinstance(guid, text_type):
                    check_output += '  required non-null string: guid\n'
                    failed += 1
                    if fix:
                        new_guid = uuid.uuid4()
                        all_guids[new_guid] = check_name
                        decoded['guid'] = new_guid
                        check_output += '  new `guid`: {}\n'.format(new_guid)
                        failed -= 1
                else:
                    all_guids[guid] = check_name

                # manifest_version
                correct_manifest_version = '1.0.0'
                manifest_version = decoded.get('manifest_version')
                version_parts = parse_version_parts(manifest_version)
                if len(version_parts) != 3:
                    if not manifest_version:
                        check_output += '  required non-null string: manifest_version\n'
                    else:
                        check_output += '  invalid `manifest_version`: {}\n'.format(manifest_version)
                    failed += 1
                    if fix:
                        version_parts = parse_version_parts(correct_manifest_version)
                        decoded['manifest_version'] = correct_manifest_version
                        check_output += '  new `manifest_version`: {}\n'.format(correct_manifest_version)
                        failed -= 1

                if len(version_parts) == 3:
                    about_exists = os.path.isfile(
                        os.path.join(check_dir, 'datadog_checks', check_name, '__about__.py')
                    )
                    if version_parts >= [1, 0, 0]:
                        if 'version' in decoded and about_exists:
                            check_output += '  outdated field: version\n'
                            failed += 1
                            if fix:
                                del decoded['version']
                                check_output += '  removed field: version\n'
                                failed -= 1

                        if 'max_agent_version' in decoded:
                            check_output += '  outdated field: max_agent_version\n'
                            failed += 1
                            if fix:
                                del decoded['max_agent_version']
                                check_output += '  removed field: max_agent_version\n'
                                failed -= 1

                        if 'min_agent_version' in decoded:
                            check_output += '  outdated field: min_agent_version\n'
                            failed += 1
                            if fix:
                                del decoded['min_agent_version']
                                check_output += '  removed field: min_agent_version\n'
                                failed -= 1
                    elif about_exists:
                        check_output += '  outdated `manifest_version`: {}\n'.format(manifest_version)
                        failed += 1
                        if fix:
                            decoded['manifest_version'] = correct_manifest_version
                            check_output += '  new `manifest_version`: {}\n'.format(correct_manifest_version)

                            if 'version' in decoded:
                                del decoded['version']
                                check_output += '  removed field: version\n'

                            if 'max_agent_version' in decoded:
                                del decoded['max_agent_version']
                                check_output += '  removed field: max_agent_version\n'

                            if 'min_agent_version' in decoded:
                                del decoded['min_agent_version']
                                check_output += '  removed field: min_agent_version\n'

                            failed -= 1
                    else:
                        version = decoded.get('version')
                        version_parts = parse_version_parts(version)
                        if len(version_parts) != 3:
                            if not version:
                                check_output += '  required non-null string: version\n'
                            else:
                                check_output += '  invalid `version`: {}\n'.format(version)
                            failed += 1

                # maintainer
                correct_maintainer = 'help@datadoghq.com'
                maintainer = decoded.get('maintainer')
                if maintainer != correct_maintainer:
                    check_output += '  incorrect `maintainer`: {}\n'.format(maintainer)
                    failed += 1
                    if fix:
                        decoded['maintainer'] = correct_maintainer
                        check_output += '  new `maintainer`: {}\n'.format(correct_maintainer)
                        failed -= 1

                # name
                correct_name = check_name
                name = decoded.get('name')
                if not isinstance(name, text_type) or name.lower() != correct_name.lower():
                    check_output += '  incorrect `name`: {}\n'.format(name)
                    failed += 1
                    if fix:
                        decoded['name'] = correct_name
                        check_output += '  new `name`: {}\n'.format(correct_name)
                        failed -= 1

                # short_description
                short_description = decoded.get('short_description')
                if not short_description or not isinstance(short_description, text_type):
                    check_output += '  required non-null string: short_description\n'
                    failed += 1

                # support
                correct_support = 'contrib' if os.path.basename(ROOT) == 'extras' else 'core'
                support = decoded.get('support')
                if support != correct_support:
                    check_output += '  incorrect `support`: {}\n'.format(support)
                    failed += 1
                    if fix:
                        decoded['support'] = correct_support
                        check_output += '  new `support`: {}\n'.format(correct_support)
                        failed -= 1

                if include_extras:
                    # supported_os
                    supported_os = decoded.get('supported_os')
                    if not supported_os or not isinstance(supported_os, list):
                        check_output += '  required non-null sequence: supported_os\n'
                        failed += 1
                    else:
                        known_systems = {'linux', 'mac_os', 'windows'}
                        unknown_systems = sorted(set(supported_os) - known_systems)
                        if unknown_systems:
                            check_output += '  unknown `supported_os`: {}\n'.format(', '.join(unknown_systems))
                            failed += 1

                    # public_title
                    public_title = decoded.get('public_title')
                    if not public_title or not isinstance(public_title, text_type):
                        check_output += '  required non-null string: public_title\n'
                        failed += 1
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
                            check_output += '  invalid `public_title`: {}\n'.format(public_title)
                            failed += 1

                    # categories
                    categories = decoded.get('categories')
                    if not categories or not isinstance(categories, list):
                        check_output += '  required non-null sequence: categories\n'
                        failed += 1

                    # type
                    correct_integration_type = 'check'
                    integration_type = decoded.get('type')
                    if not integration_type or not isinstance(integration_type, text_type):
                        check_output += '  required non-null string: type\n'
                        failed += 1
                        if fix:
                            decoded['type'] = correct_integration_type
                            check_output += '  new `type`: {}\n'.format(correct_integration_type)
                            failed -= 1
                    elif integration_type != correct_integration_type:
                        check_output += '  invalid `type`: {}\n'.format(integration_type)
                        failed += 1
                        if fix:
                            decoded['type'] = correct_integration_type
                            check_output += '  new `type`: {}\n'.format(correct_integration_type)
                            failed -= 1

                    # is_public
                    correct_is_public = True
                    is_public = decoded.get('is_public')
                    if not isinstance(is_public, bool):
                        check_output += '  required boolean: is_public\n'
                        failed += 1
                        if fix:
                            decoded['is_public'] = correct_is_public
                            check_output += '  new `is_public`: {}\n'.format(correct_is_public)
                            failed -= 1
                    elif is_public != correct_is_public:
                        check_output += '  invalid `is_public`: {}\n'.format(is_public)
                        failed += 1
                        if fix:
                            decoded['is_public'] = correct_is_public
                            check_output += '  new `is_public`: {}\n'.format(correct_is_public)
                            failed -= 1

                    # has_logo
                    default_has_logo = True
                    has_logo = decoded.get('has_logo')
                    if not isinstance(has_logo, bool):
                        check_output += '  required boolean: has_logo\n'
                        failed += 1
                        if fix:
                            decoded['has_logo'] = default_has_logo
                            check_output += '  new `has_logo`: {}\n'.format(default_has_logo)
                            failed -= 1

                    # doc_link
                    doc_link = decoded.get('doc_link')
                    if not doc_link or not isinstance(doc_link, text_type):
                        check_output += '  required non-null string: doc_link\n'
                        failed += 1
                    elif not doc_link.startswith('https://docs.datadoghq.com/integrations/'):
                        check_output += '  invalid `doc_link`: {}\n'.format(doc_link)
                        failed += 1

            # See if anything happened
            if len(check_output.splitlines()) > 1:
                output += check_output
                if fix or update:
                    new_manifest = '{}\n'.format(json.dumps(decoded, indent=2, separators=(',', ': ')))
                    with open(manifest_file, 'w') as f:
                        f.write(new_manifest)

    if output:
        # Don't print trailing new line
        print(output[:-1])

    raise Exit(int(failed > 0))
