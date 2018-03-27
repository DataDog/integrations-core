from __future__ import print_function, unicode_literals

import json
import os
import uuid
from collections import OrderedDict
from io import open

from invoke import task
from invoke.exceptions import Exit

ROOT = os.path.dirname(os.path.abspath(__file__))

# Note: these are the names of the folder containing the check
AGENT_BASED_INTEGRATIONS = [
    'datadog-checks-base',
    'disk',
    'envoy',
    'istio',
    'kube_proxy',
    'kubelet',
    'linkerd',
    'prometheus',
    'vsphere',
]


def parse_version_parts(version):
    return (
        [int(v) for v in version.split('.') if v.isdigit()]
        if isinstance(version, str) else []
    )


def ensure_deps_declared(reqs_txt, reqs_in):
    if os.path.isfile(reqs_txt) and not os.path.isfile(reqs_in):
        declacred_lines = []

        with open(reqs_txt, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            line = line.split('--hash')[0].strip('\r\n \\')
            if line and not line.startswith('#'):
                declacred_lines.append(line + '\n')

        with open(reqs_in, 'w', encoding='utf-8') as f:
            f.writelines(declacred_lines)


@task(help={
    'targets': "Comma separated names of the checks that will be tested",
    'changed-only': "Whether to only test checks that were changed in a PR",
    'dry-run': "Just print the list of checks that would be tested",
})
def test(ctx, targets=None, changed_only=False, dry_run=False):
    """
    Run the tests for Agent-based checks

    Example invocation:
        inv test --targets=disk,redisdb
    """
    if targets is None:
        targets = AGENT_BASED_INTEGRATIONS
    elif isinstance(targets, basestring):
        targets = [t for t in targets.split(',') if t in AGENT_BASED_INTEGRATIONS]

    if changed_only:
        targets = list(set(targets) & integrations_changed(ctx))

    if dry_run:
        print(targets)
        return

    for check in targets:
        with ctx.cd(check):
            print("\nRunning tox in '{}'\n".format(check))
            ctx.run('tox')


def integrations_changed(ctx):
    """
    Find out which checks were changed in the current branch
    """
    checks = set()
    res = ctx.run('git diff --name-only master...', hide='out')
    for line in res.stdout.split('\n'):
        if line:
            checks.add(line.split('/')[0])
    return checks


@task(help={
    'package': 'The package to upgrade throughout the integrations',
    'version': 'The version of the package to pin',
    'verbose': 'Whether or not to produce output',
})
def upgrade(ctx, package=None, version=None, verbose=False):
    """Upgrade a dependency for all integrations that require it.
    ``pip-compile`` must be in PATH.

    Example invocation:
        inv upgrade --verbose -p=requests -v=2.18.4
    """
    if not (package and version):
        raise Exit('`package` and `version` are required arguments.')

    for check_name in sorted(os.listdir(ROOT)):
        check_dir = os.path.join(ROOT, check_name)
        reqs_in = os.path.join(check_dir, 'requirements.in')
        reqs_txt = os.path.join(check_dir, 'requirements.txt')

        ensure_deps_declared(reqs_txt, reqs_in)

        if os.path.isfile(reqs_in):
            with open(reqs_in, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                try:
                    pkg = line.split('=')[0].strip()
                    if pkg == package:
                        break
                except IndexError:
                    continue
            # Skip integrations that don't require the package.
            else:
                continue

            if verbose:
                print('Check `{}`:'.format(check_name))
                print('    Old: `{}`'.format(lines[i].strip()))

            lines[i] = '{}=={}\n'.format(package, version)

            with open(reqs_in, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            if verbose:
                print('    New: `{}`'.format(lines[i].strip()))
                print('    Locking dependencies...')

            with ctx.cd(check_dir):
                ctx.run(
                    'pip-compile '
                    '--generate-hashes '
                    '--output-file requirements.txt '
                    'requirements.in',
                    hide='both'
                )


@task(help={
    'update': 'Update every `manifest_version`',
    'fix': 'Attempt making manifests valid',
    'include_extras': 'Include optional fields',
})
def manifest(ctx, update=None, fix=False, include_extras=False):
    """Validate all `manifest.json` files.

    Example invocation:
        inv manifest --update 1.0.0
    """
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
                decoded['manifest_version'] = update
                check_output += '  new `manifest_version`: {}\n'.format(update)
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
                elif not guid or not isinstance(guid, str):
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

                if len(version_parts) == 3 and version_parts >= [1, 0, 0]:
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
                            del decoded['max_agent_version']
                            check_output += '  removed field: min_agent_version\n'
                            failed -= 1

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
                if not isinstance(name, str) or name.lower() != correct_name.lower():
                    check_output += '  incorrect `name`: {}\n'.format(name)
                    failed += 1
                    if fix:
                        decoded['name'] = correct_name
                        check_output += '  new `name`: {}\n'.format(correct_name)
                        failed -= 1

                # short_description
                short_description = decoded.get('short_description')
                if not short_description or not isinstance(short_description, str):
                    check_output += '  required non-null string: short_description\n'
                    failed += 1

                # support
                correct_support = 'contrib' if os.path.basename(ROOT) == 'extras' else 'core'
                support = decoded.get('support')
                if support not in ('core', 'contrib'):
                    check_output += '  invalid `support`: {}\n'.format(support)
                    failed += 1
                    if fix:
                        decoded['support'] = correct_support
                        check_output += '  new `support`: {}\n'.format(correct_support)
                        failed -= 1

                # version
                version = decoded.get('version')
                version_parts = parse_version_parts(version)
                if len(version_parts) != 3:
                    if not version:
                        check_output += '  required non-null string: version\n'
                    else:
                        check_output += '  invalid `version`: {}\n'.format(version)
                    failed += 1

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
                    if not public_title or not isinstance(public_title, str):
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

            # See if anything happened
            if len(check_output.splitlines()) > 1:
                output += check_output
                if fix or update:
                    new_manifest = '{}\n'.format(json.dumps(decoded, indent=2))
                    with open(manifest_file, 'w') as f:
                        f.write(new_manifest)

    if output:
        # Don't print trailing new line
        print(output[:-1])

    raise Exit(int(failed > 0))













