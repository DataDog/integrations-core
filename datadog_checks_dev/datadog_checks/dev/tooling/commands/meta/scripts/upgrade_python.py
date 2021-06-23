# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import click

from .....fs import file_exists, path_join, read_file_binary, resolve_dir_contents, write_file_binary
from ....constants import get_root
from ...console import CONTEXT_SETTINGS, echo_success


def version_string_to_int(s):
    return int(s.replace('.', ''))


def get_replacer(new_version):
    new = str(new_version).encode('utf-8')

    def replacer(match):
        # Replace the first occurrence of the captured group with the new version
        return match.group(0).replace(match.groupdict()['old_version'], new, 1)

    return replacer


@click.command(
    'upgrade-python', context_settings=CONTEXT_SETTINGS, short_help='Upgrade Python version of all test environments'
)
@click.argument('new_version')
@click.argument('old_version', required=False)
def upgrade_python(new_version, old_version):
    """Upgrade the Python version of all test environments.

    \b
    `$ ddev meta scripts upgrade-python 3.8`
    """
    root = get_root()

    new_version = version_string_to_int(new_version)
    old_version = version_string_to_int(old_version) if old_version else new_version - 1

    # Examples:
    #
    # basepython = py37
    # py{27,37}: e2e ready
    # py37-{10,11}
    tox_pattern = re.compile(br'\s+py[{,\d]*(?P<old_version>%d)' % old_version, re.MULTILINE)
    replacer = get_replacer(new_version)

    files_changed = 0
    for check_dir in resolve_dir_contents(root):
        tox_file = path_join(check_dir, 'tox.ini')
        if not file_exists(tox_file):
            continue

        original_tox_contents = read_file_binary(tox_file)
        new_tox_contents = tox_pattern.sub(replacer, original_tox_contents)

        if new_tox_contents != original_tox_contents:
            files_changed += 1
            write_file_binary(tox_file, new_tox_contents)

    echo_success(f'Updated {files_changed} files')
