# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import shutil

from in_toto import runlib
from in_toto.gpg.constants import GPG_COMMAND

from .constants import get_root
from ..subprocess import run_command
from ..utils import (
    chdir, ensure_dir_exists, path_join, stream_file_lines, write_file
)

LINK_DIR = '.links'
STEP_NAME = 'tag'


def read_gitignore_patterns():
    exclude_patterns = []

    for line in stream_file_lines('.gitignore'):
        line = line.strip()
        if line and not line.startswith('#'):
            exclude_patterns.append(line)

    return exclude_patterns


def get_key_id(gpg_exe):
    result = run_command('{} --card-status'.format(gpg_exe), capture='out', check=True)
    lines = result.stdout.splitlines()
    for line in lines:
        if line.startswith('Signature key ....:'):
            return line.split(':')[1].replace(' ', '')
    else:
        raise Exception('Could not find private signing key on Yubikey!')


def run_in_toto(key_id, products):
    exclude_patterns = read_gitignore_patterns()

    runlib.in_toto_run(
        # Do not record files matching these patterns.
        exclude_patterns=exclude_patterns,
        # Use this GPG key.
        gpg_keyid=key_id,
        # Do not execute any other command.
        link_cmd_args=[],
        # Do not record anything as input.
        material_list=None,
        # Use this step name.
        name=STEP_NAME,
        # Record every source file, except for exclude_patterns, as output.
        product_list=products,
        # Keep file size down
        compact_json=True,
    )


def update_link_metadata(checks):
    root = get_root()
    ensure_dir_exists(path_join(root, LINK_DIR))

    # Sign only what affects each wheel
    products = []
    for check in checks:
        products.append(path_join(check, 'datadog_checks'))
        products.append(path_join(check, 'setup.py'))

    key_id = get_key_id(GPG_COMMAND)

    # Find this latest signed link metadata file on disk.
    # NOTE: in-toto currently uses the first 8 characters of the signing keyId.
    key_id_prefix = key_id[:8].lower()
    tag_link = '{}.{}.link'.format(STEP_NAME, key_id_prefix)

    # Final location of metadata file.
    metadata_file = path_join(LINK_DIR, tag_link)

    # File used to tell the pipeline where to find the latest metadata file.
    metadata_file_tracker = path_join(LINK_DIR, 'LATEST')

    with chdir(root):
        run_in_toto(key_id, products)

        # Tell pipeline which tag link metadata to use.
        write_file(metadata_file_tracker, tag_link)

        # Move it to the expected location.
        shutil.move(tag_link, metadata_file)

    return metadata_file, metadata_file_tracker
