# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import glob
import logging
import os
import re
import shutil
import string
import subprocess
from collections import defaultdict, namedtuple

import requests
from packaging.version import parse as parse_version
from six import iteritems
from six.moves.urllib_parse import urljoin
from tenacity import retry, stop_after_attempt, wait_exponential

from datadog_checks.downloader.download import REPOSITORY_URL_PREFIX

log = logging.getLogger('test_downloader')
IntegrationMetadata = namedtuple("IntegrationMetadata", ["version", "root_layout_type"])


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


@retry(wait=wait_exponential(min=2, max=60), stop=stop_after_attempt(10))
def download(package, version=None, root_layout_type='core'):
    """
    TODO: Flaky downloader
    Why we need a retry here?

    The issue with the flake here is that:
    - When downloading the first package, the datadog_checks_downloader will also download the signing metadata and
      especially "timestamp.json" which gives the current "version". Anytime a new package is pushed, that version
      gets increased.
    - When downloading package A, datadog_checks_downloader will write to disk the current version of "timestamp.json"
    - When downloading package B, datadog_checks_downloader will check the current version of timestamp.json against
      the local one and will fail here if it finds an older version on the repo.

    Retrying should help test not to fail, but the real issue describe above still need to be solved.
    Users relying on it for automated deploys and install can face the same issue.
    Source: https://github.com/DataDog/integrations-core/pull/6476#issuecomment-619059117
    """
    # -v:     CRITICAL
    # -vv:    ERROR
    # -vvv:   WARNING
    # -vvvv:  INFO
    # -vvvvv: DEBUG
    cmd = ['python', '-m', 'datadog_checks.downloader', '-vvvv', '--type', root_layout_type]
    if version:
        cmd.extend(['--version', version])
    cmd.append(package)
    out = subprocess.check_output(cmd)
    log.debug(' '.join(cmd))
    log.debug(out)
    log.debug('')


def fetch_all_targets():
    targets = {}
    log.debug("Downloading wheels-signer data...")
    for c in list(string.ascii_lowercase):
        url = urljoin(REPOSITORY_URL_PREFIX, 'metadata.staged/wheels-signer-{}.json'.format(c))
        r = requests.get(url)
        r.raise_for_status()
        targets.update(r.json()['signed']['targets'])
    return targets


def get_all_integrations_metadata():
    """
    This function parses the content of 'targets' in order to generate a list of integrations to test
    with some metadata.
    This metadata is a tuple of (version, root_layout_type):
        - version: Is the latest (non-rc) version of an integration
        - root_layout_type: 'extras' or 'core' based on the type of integration."""
    PATTERN = r'simple/(datadog-[\w-]+?)/datadog_[\w-]+?-(.*)-py\d.*.whl'
    results = defaultdict(lambda: IntegrationMetadata("0.0.0", "root"))
    targets = fetch_all_targets()
    for target, metadata in iteritems(targets):
        match = re.match(PATTERN, target)
        if not match:
            # An html file, safe to ignore
            continue
        integration_name, version = match.groups()
        root_layout_type = metadata['custom']['root-layout-type']
        assert root_layout_type in ('core', 'extras')
        known_version = results[integration_name].version
        if parse_version(known_version) < parse_version(version):
            # The test only downloads the latest integrations versions.
            results[integration_name] = IntegrationMetadata(version, root_layout_type)

    return dict(results)


def test_downloader():
    integrations_metadata = get_all_integrations_metadata()
    # The regex corresponding to package names in a global simple index.
    HTML_PATTERN = r"<a href='(datadog-[\w-]+?)/'>\w+?</a><br />"

    # Download the global simple index, which contains all known package names.
    index = urljoin(REPOSITORY_URL_PREFIX, 'targets/simple/index.html')
    r = requests.get(index)
    r.raise_for_status()

    try:
        for line in r.text.split('\n'):
            match = re.match(HTML_PATTERN, line)
            if not match:
                continue
            integration_name = match.group(1)
            if integration_name not in integrations_metadata:
                raise Exception(
                    "Integration '{}' is in the simple index but does not have tuf metadata.".format(integration_name)
                )
            version, root_layout_type = integrations_metadata[integration_name]
            if match:
                download(match.group(1), version, root_layout_type)
    finally:
        cleanup()
