# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import click

from .....utils import file_exists, path_join, read_file_binary, resolve_dir_contents, write_file_binary
from ....constants import get_root
from ...console import CONTEXT_SETTINGS, echo_success


def version_string_to_int(s):
    return int(s.replace('.', ''))


def get_replacer(new_version):
    new = str(new_version).encode('utf-8')

    def replacer(match):
        return match.group(0).replace(match.group(1), new, 1)

    return replacer


@click.command(
    'upgrade-python', context_settings=CONTEXT_SETTINGS, short_help='Upgrade Python version of all test environments'
)
@click.argument('new')
@click.argument('old', required=False)
def upgrade_python(new, old):
    """Upgrade the Python version of all test environments.

    \b
    $ ddev meta scripts upgrade-python 3.8
    Updated 125 files
    """
    root = get_root()

    new = version_string_to_int(new)
    old = version_string_to_int(old) if old else new - 1

    tox_pattern = re.compile(br'\s+py[{,\d]*(%d)' % old, re.MULTILINE)
    replacer = get_replacer(new)

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
