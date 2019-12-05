# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import glob
import logging
import os
import re
import shutil
import subprocess

import requests
import six

from datadog_checks.downloader.download import REPOSITORY_URL_PREFIX

log = logging.getLogger('test_downloader')


def delete_files(files):
    for f in files:
        os.remove(f)


def cleanup():
    REPO_DIR = 'datadog_checks/downloader/data/repo/'

    METADATA_DIR = os.path.join(REPO_DIR, 'metadata')
    TARGETS_DIR = os.path.join(REPO_DIR, 'targets')
    IN_TOTO_METADATA_DIR = os.path.join(TARGETS_DIR, 'in-toto-metadata')
    IN_TOTO_PUBKEYS_DIR = os.path.join(TARGETS_DIR, 'in-toto-pubkeys')
    SIMPLE_DIR = os.path.join(TARGETS_DIR, 'simple')

    # First, nuke all known targets. but not the directory for targets itself.
    shutil.rmtree(IN_TOTO_METADATA_DIR)
    shutil.rmtree(IN_TOTO_PUBKEYS_DIR)
    shutil.rmtree(SIMPLE_DIR)

    # Then, nuke all previous TUF metadata.
    previous_jsons = os.path.join(METADATA_DIR, 'previous/*.json')
    previous_jsons = glob.glob(previous_jsons)
    delete_files(previous_jsons)

    # Finally, nuke ALL current TUF metadata EXCEPT the unversioned root metadata.
    current_jsons = os.path.join(METADATA_DIR, 'current/*.json')
    current_jsons = glob.glob(current_jsons)
    current_jsons = [c for c in current_jsons if os.path.basename(c) != 'root.json']
    delete_files(current_jsons)


def download(package):
    # -v:     CRITICAL
    # -vv:    ERROR
    # -vvv:   WARNING
    # -vvvv:  INFO
    # -vvvvv: DEBUG
    cmd = ['datadog-checks-downloader', '-vvvv', package]
    out = subprocess.check_output(cmd)
    log.debug(' '.join(cmd))
    log.debug(out)
    log.debug('')


def test_downloader():
    # The regex corresponding to package names in a global simple index.
    PATTERN = r"<a href='(datadog-[\w-]+?)/'>\w+?</a><br />"

    # Download the global simple index, which contains all known package names.
    index = six.moves.urllib_parse.urljoin(REPOSITORY_URL_PREFIX, 'targets/simple/index.html')
    r = requests.get(index)
    r.raise_for_status()

    try:
        for line in r.text.split('\n'):
            match = re.match(PATTERN, line)

            if match:
                download(match.group(1))
    finally:
        cleanup()
