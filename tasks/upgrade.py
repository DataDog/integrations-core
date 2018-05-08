# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals

import os

from invoke import task
from invoke.exceptions import Exit

from .constants import ROOT


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
