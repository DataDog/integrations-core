# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# flake8: noqa
import json
import os
import shutil

# How long ddev will wait for GPG to finish, especially when asking dev for signature.
import securesystemslib.settings
securesystemslib.settings.SUBPROCESS_TIMEOUT = 60

from securesystemslib.gpg.constants import GPG_COMMAND

from in_toto import runlib

from .constants import get_root
from .git import ignored_by_git, tracked_by_git
from ..subprocess import run_command
from ..utils import chdir, ensure_dir_exists, path_join, stream_file_lines

LINK_DIR = '.in-toto'
STEP_NAME = 'tag'


class YubikeyException(Exception):
    pass


class NeitherTrackedNorIgnoredFileException(Exception):
    def __init__(self, filename):
        self.filename = filename


    def __str__(self):
        return f'{self.filename} has neither been tracked nor ignored by git and in-toto!'


class UntrackedButIgnoredFileException(Exception):
    def __init__(self, filename):
        self.filename = filename


    def __str__(self):
        return f'{self.filename} has not been tracked, but it should be ignored by git and in-toto!'


def read_gitignore_patterns():
    exclude_patterns = []

    for line in stream_file_lines('.gitignore'):
        line = line.strip()
        if line and not line.startswith('#'):
            exclude_patterns.append(line)

    return exclude_patterns


def get_key_id(gpg_exe):
    result = run_command(f'{gpg_exe} --card-status', capture='out', check=True)
    lines = result.stdout.splitlines()
    for line in lines:
        if line.startswith('Signature key ....:'):
            return line.split(':')[1].replace(' ', '')
    else:
        raise YubikeyException('Could not find private signing key on Yubikey!')


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
        # Cross-platform support
        normalize_line_endings=True,
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
    tag_link = f'{STEP_NAME}.{key_id_prefix}.link'

    # Final location of metadata file.
    metadata_file = path_join(LINK_DIR, tag_link)

    with chdir(root):
        # We should ignore products untracked and ignored by git.
        run_in_toto(key_id, products)

        # Check whether each signed product is being tracked AND ignored by git.
        # NOTE: We have to check now *AFTER* signing the tag link file, so that
        # we can check against the actual complete list of products.
        with open(tag_link) as tag_json:
            tag = json.load(tag_json)
            products = tag['signed']['products']

        for product in products:
            # If NOT tracked...
            if not tracked_by_git(product):
                # First, delete the tag link off disk so as not to pollute.
                os.remove(tag_link)

                # AND NOT ignored, then it most likely means the developer
                # forgot to add the file to git.
                if not ignored_by_git(product):
                    raise NeitherTrackedNorIgnoredFileException(product)
                # AND ignored, then it most likely means that incorrectly
                # recorded with in-toto files ignored by git.
                else:
                    raise UntrackedButIgnoredFileException(product)

        # Move it to the expected location.
        shutil.move(tag_link, metadata_file)

    return (metadata_file,)
