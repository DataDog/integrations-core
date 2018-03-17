from __future__ import print_function, unicode_literals

import os
from contextlib import contextmanager
from io import open

from invoke import task

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


@contextmanager
def chdir(d, cwd=None):
    origin = cwd or os.getcwd()
    os.chdir(d)

    try:
        yield
    finally:
        os.chdir(origin)


def ensure_deps_declared(reqs_txt, reqs_in):
    if os.path.isfile(reqs_txt) and not os.path.isfile(reqs_in):
        declacred_lines = []

        with open(reqs_txt, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            line = line.split('--hash')[0].strip('\r\n \\')
            if line and not line.startswith('#'):
                declacred_lines.append(line + '\n')

        with open(reqs_in, 'w', encoding='utf-8', newline='\n') as f:
            f.writelines(declacred_lines)


@task(help={
    'targets': "Comma separated names of the checks that will be tested",
    'changed-only': "Whether to only test checks that were changed in a PR",
    'dry-run': "Just print the list of checks that would be tested",
})
def test(ctx, targets=None, changed_only=False, dry_run=False):
    """
    Run the tests for Agent-based checks

    Example invokation:
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
def upgrade(ctx, package, version, verbose=False):
    here = os.path.dirname(os.path.abspath(__file__))

    for check_name in sorted(os.listdir(here)):
        check_dir = os.path.join(here, check_name)
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
            else:
                continue

            if verbose:
                print('Check `{}`:'.format(check_name))
                print('    Old: `{}`'.format(lines[i].strip()))

            lines[i] = '{}=={}\n'.format(package, version)

            with open(reqs_in, 'w', encoding='utf-8', newline='\n') as f:
                f.writelines(lines)

            if verbose:
                print('    New: `{}`'.format(lines[i].strip()))
                print('    Locking dependencies...')

            with chdir(check_dir):
                ctx.run(
                    'pip-compile '
                    '--generate-hashes '
                    '--output-file requirements.txt '
                    'requirements.in',
                    hide='both'
                )
