from __future__ import print_function, unicode_literals

import json
import os
from collections import OrderedDict, defaultdict
from io import open

from invoke import task
from invoke.exceptions import Exit

HERE = os.path.dirname(os.path.abspath(__file__))

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

    for check_name in sorted(os.listdir(HERE)):
        check_dir = os.path.join(HERE, check_name)
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
    'alter': 'Attempt making manifests valid',
})
def manifest(ctx, update=None, alter=False):
    """Validate all `manifest.json` files.

    Example invocation:
        inv manifest --update 1.0.0
    """
    guids = defaultdict(list)
    failed = 0
    output = ''

    for check_name in sorted(os.listdir(HERE)):
        check_dir = os.path.join(HERE, check_name)
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

            # maintainer
            correct_maintainer = 'help@datadoghq.com'
            maintainer = decoded.get('maintainer')
            if maintainer != correct_maintainer:
                check_output += '  incorrect `maintainer`: {}\n'.format(maintainer)
                failed += 1
                if alter:
                    decoded['maintainer'] = correct_maintainer
                    check_output += '  new `maintainer`: {}\n'.format(correct_maintainer)
                    failed -= 1

            # manifest_version
            if update:
                decoded['manifest_version'] = update
                check_output += '  new `manifest_version`: {}\n'.format(update)

            correct_manifest_version = '1.0.0'
            manifest_version = decoded.get('manifest_version')
            if not isinstance(manifest_version, str) or len([v for v in manifest_version.split('.') if v]) != 3:
                check_output += '  invalid `manifest_version`: {}\n'.format(manifest_version)
                failed += 1
                if alter:
                    decoded['manifest_version'] = correct_manifest_version
                    check_output += '  new `manifest_version`: {}\n'.format(correct_manifest_version)
                    failed -= 1

            if len(check_output.splitlines()) > 1:
                output += check_output
                if alter or update:
                    with open(manifest_file, 'w') as f:
                        f.write('{}\n'.format(json.dumps(decoded, indent=2)))

    if output:
        # Don't print trailing new line
        print(output[:-1])

    raise Exit(int(failed > 0))













