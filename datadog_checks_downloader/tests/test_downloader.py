# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import logging
import os
import pathlib
import random
import re
import shutil
import string
import subprocess
import sys
from collections import defaultdict, namedtuple
from datetime import datetime
from urllib.parse import urljoin

import pytest
import requests
from freezegun import freeze_time
from packaging.version import parse as parse_version
from tenacity import retry, stop_after_attempt, wait_exponential
from tuf.api.exceptions import DownloadError, ExpiredMetadataError, RepositoryError, UnsignedMetadataError

import datadog_checks.downloader
from datadog_checks.downloader.cli import download
from datadog_checks.downloader.download import REPOSITORY_URL_PREFIX
from datadog_checks.downloader.exceptions import NonDatadogPackage, NoSuchDatadogPackage
from tests.local_http import local_http_server, local_http_server_local_dir

_LOGGER = logging.getLogger("test_downloader")

# Preserve datetime to make sure tests that use local metadata do not expire.
_LOCAL_TESTS_DATA_TIMESTAMP = datetime(year=2022, month=7, day=25)

# Used to test local metadata expiration.
_LOCAL_TESTS_DATA_TIMESTAMP_EXPIRED = datetime(year=2522, month=1, day=1)

# The regex corresponding to package names in a global simple index.
_HTML_PATTERN_RE = re.compile(r"<a href='(datadog-[\w-]+?)/'>\w+?</a><br />")

# Number of integrations to test. This eliminates timeouts in CI.
_TEST_DOWNLOADER_SAMPLE_SIZE = 10

IntegrationMetadata = namedtuple("IntegrationMetadata", ["version", "root_layout_type"])

# Integrations released for the last time by a revoked developer but not shipped anymore.
EXCLUDED_INTEGRATIONS = [
    "datadog-docker-daemon",
    "datadog-dd-cluster-agent",  # excluding this since actual integration is called `datadog-cluster-agent`
    "datadog-kubernetes",  # excluding this since `kubernetes` check is Agent v5 only
]

# Specific integration versions released for the last time by a revoked developer but not shipped anymore.
EXCLUDED_INTEGRATION_VERSION = [
    "simple/datadog-ibm-mq/datadog_ibm_mq-4.1.0rc1-py2.py3-none-any.whl",
    "simple/datadog-network/datadog_network-9.1.1rc1-py2.py3-none-any.whl",
]


def _do_run_downloader(argv):
    """Run the Datadog checks downloader."""
    old_sys_argv = sys.argv

    sys.argv = ["datadog_checks_downloader"] + argv  # Make sure argv[0] (program name) is prepended.
    try:
        download()
    finally:
        sys.argv = old_sys_argv


@pytest.mark.online
def test_download(capfd, distribution_name, distribution_version, temporary_local_repo):
    """Test datadog-checks-downloader successfully downloads and validates a wheel file."""
    argv = [distribution_name, "--version", distribution_version]

    _do_run_downloader(argv)
    stdout, stderr = capfd.readouterr()

    assert not stderr, "No standard error expected, got: {}".format(stderr)

    output = [line for line in stdout.splitlines() if line]
    assert len(output) == 1, "Only one output line expected, got {}:\n\t{}".format(len(output), stdout)

    expected_output = r"{}/repo/targets/simple/{}/{}-{}-.*?\.whl".format(
        pathlib.PurePath(temporary_local_repo).as_posix(),
        distribution_name,
        distribution_name.replace("-", "_"),
        distribution_version,
    )
    assert re.match(expected_output, output[0]), "Expected '{}' to match '{}'".format(output[0], expected_output)


@pytest.mark.online
def test_expired_metadata_error(distribution_name, distribution_version):
    """Test expiration of metadata raises an exception."""
    argv = [distribution_name, "--version", distribution_version]

    # Make sure we use a time far enough into the future.
    with freeze_time("2524-01-01"), pytest.raises(ExpiredMetadataError):
        _do_run_downloader(argv)


@pytest.mark.offline
def test_non_datadog_distribution():
    """Test checking non-datadog distribution."""
    argv = ["some-distribution", "--version", "1.0.0"]

    with pytest.raises(NonDatadogPackage, match="some-distribution"):
        _do_run_downloader(argv)


@pytest.mark.offline
@pytest.mark.parametrize(
    "distribution_name,distribution_version,target",
    [
        (
            "datadog-active-directory",
            "1.10.0",
            "simple/datadog-active-directory/datadog_active_directory-1.10.0-py2.py3-none-any.whl",
        ),
    ],
)
@freeze_time(_LOCAL_TESTS_DATA_TIMESTAMP)
def test_local_download(capfd, distribution_name, distribution_version, target):
    """Test local verification of a wheel file."""

    with local_http_server("{}-{}".format(distribution_name, distribution_version)) as http_url:
        argv = [
            distribution_name,
            "--version",
            distribution_version,
            "--repository",
            http_url,
        ]
        _do_run_downloader(argv)

    stdout, _ = capfd.readouterr()

    output = [line for line in stdout.splitlines() if line]
    assert len(output) == 1, "Only one output line expected, got {}:\n\t{}".format(len(output), stdout)
    assert output[0].endswith(target)


@pytest.mark.local_dir
def test_local_dir_download(capfd, local_dir, distribution_name, distribution_version):
    """Test local verification of a wheel file."""
    if local_dir is None:
        pytest.skip("no local directory explicitly passed")

    with local_http_server_local_dir(local_dir) as http_url:
        argv = [
            distribution_name,
            "--version",
            distribution_version,
            "--repository",
            http_url,
        ]
        _do_run_downloader(argv)

    stdout, _ = capfd.readouterr()

    output = [line for line in stdout.splitlines() if line]
    assert len(output) == 1, "Only one output line expected, got {}:\n\t{}".format(len(output), stdout)
    assert distribution_name in output[0]
    assert distribution_version in output[0]
    assert output[0].endswith(".whl")


@pytest.mark.offline
@pytest.mark.parametrize(
    "distribution_name,distribution_version",
    [
        ("datadog-active-directory", "1.10.0"),
    ],
)
def test_local_expired_metadata_error(distribution_name, distribution_version):
    """Test expiration of metadata raises an exception."""
    with local_http_server("{}-{}".format(distribution_name, distribution_version)) as http_url:
        argv = [
            distribution_name,
            "--version",
            distribution_version,
            "--repository",
            http_url,
        ]

        # Make sure we use a time far enough into the future.
        with freeze_time(_LOCAL_TESTS_DATA_TIMESTAMP_EXPIRED), pytest.raises(ExpiredMetadataError):
            _do_run_downloader(argv)


@pytest.mark.offline
def test_local_unreachable_repository():
    """Test unreachable repository raises an exception."""
    argv = [
        "datadog-some-distribution",
        "--version",
        "1.0.0",
        "--repository",
        "http://localhost:1",
    ]

    with pytest.raises(DownloadError):
        _do_run_downloader(argv)


@pytest.mark.offline
@pytest.mark.parametrize(
    "distribution_name,distribution_version",
    [
        ("datadog-active-directory", "1.10.0"),
    ],
)
@freeze_time(_LOCAL_TESTS_DATA_TIMESTAMP)
def test_local_wheels_signer_signature_leaf_error(distribution_name, distribution_version):
    """Test failure in verifying wheels-signer signature.

    The wheel-signer-{a-z} metadata has to have wrong signature.
    """

    def tamper(repo_dir):
        """Modify a signature to make it incorrect"""
        file_to_change = next((repo_dir / 'metadata.staged').glob('*.wheels-signer-a.json'))
        with open(file_to_change) as f:
            signer_metadata = json.load(f)

        signer_metadata['signatures'][0]['sig'] = 'f' * 64
        with open(file_to_change, 'w') as f:
            json.dump(signer_metadata, f)

    with local_http_server("{}-{}".format(distribution_name, distribution_version), tamper=tamper) as http_url:
        argv = [
            distribution_name,
            "--version",
            distribution_version,
            "--repository",
            http_url,
        ]

        with pytest.raises(UnsignedMetadataError, match="^wheels-signer-a was signed by 0/1 keys$"):
            _do_run_downloader(argv)


@pytest.mark.offline
@freeze_time(_LOCAL_TESTS_DATA_TIMESTAMP)
def test_local_tampered_target_triggers_failure():

    distribution_name = "datadog-active-directory"
    distribution_version = "1.10.0"

    def tamper(repo_dir):
        """Modify the target that we want to download."""
        files_to_change = (repo_dir / 'targets' / 'simple' / 'datadog-active-directory').glob(
            '*.datadog_active_directory-1.10.0-*.whl'
        )

        for path in files_to_change:
            # We make a modification that doesn't change the length so that we
            # don't trigger an error based simply on length.
            with open(path, 'r+b') as f:
                f.write(b'garbage')

    with local_http_server("{}-{}".format(distribution_name, distribution_version), tamper=tamper) as http_url:
        argv = [
            distribution_name,
            "--version",
            distribution_version,
            "--repository",
            http_url,
        ]

        with pytest.raises(RepositoryError, match="does not match expected hash"):
            _do_run_downloader(argv)


@pytest.mark.offline
@freeze_time(_LOCAL_TESTS_DATA_TIMESTAMP)
def test_local_download_non_existing_package():
    """Test local verification of a wheel file."""

    with local_http_server("datadog-active-directory-1.10.0".format()) as http_url:
        argv = [
            "datadog-a-nonexisting",
            "--version",
            "1.0.0",
            "--repository",
            http_url,
        ]
        with pytest.raises(NoSuchDatadogPackage):
            _do_run_downloader(argv)


def delete_files(files):
    for f in files:
        os.remove(f)


@pytest.fixture
def restore_repo_state(tmp_path):
    """
    Backs up the state of the data folder to restore it after the test.

    This is needed for tests that invoke the downloader from a subprocess.
    """
    # PY2's os.path prefers strings
    tmp_path = str(tmp_path)

    src_dir = os.path.join(os.path.dirname(datadog_checks.downloader.__file__), 'data')
    dst_dir = os.path.join(tmp_path, 'data')
    shutil.copytree(src_dir, dst_dir)
    yield
    shutil.rmtree(src_dir)
    shutil.copytree(dst_dir, src_dir)


@retry(wait=wait_exponential(min=2, max=60), stop=stop_after_attempt(10))
def _do_download(package, version=None, root_layout_type="core"):
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
    cmd = [
        sys.executable,
        "-m",
        "datadog_checks.downloader",
        "-vvvv",
        "--type",
        root_layout_type,
        "--ignore-python-version",
    ]
    if version:
        cmd.extend(["--version", version])
    cmd.append(package)
    _LOGGER.info("Executing %r", cmd)
    out = subprocess.check_output(cmd)
    _LOGGER.debug(" ".join(cmd))
    _LOGGER.debug(out)
    _LOGGER.debug("")


def fetch_all_targets():
    targets = {}
    _LOGGER.debug("Downloading wheels-signer data...")
    for c in list(string.ascii_lowercase):
        url = urljoin(REPOSITORY_URL_PREFIX, "metadata.staged/wheels-signer-{}.json".format(c))
        r = requests.get(url)
        r.raise_for_status()
        targets.update(r.json()["signed"]["targets"])
    return targets


def get_all_integrations_metadata():
    """
    This function parses the content of 'targets' in order to generate a list of integrations to test
    with some metadata.
    This metadata is a tuple of (version, root_layout_type):
        - version: Is the latest (non-rc) version of an integration
        - root_layout_type: 'extras' or 'core' based on the type of integration."""
    PATTERN = r"simple/(datadog-[\w-]+?)/datadog_[\w-]+?-(.*)-py\d.*.whl"
    results = defaultdict(lambda: IntegrationMetadata("0.0.0", "root"))
    targets = fetch_all_targets()
    for target, metadata in targets.items():
        match = re.match(PATTERN, target)
        if not match:
            # An html file, safe to ignore
            continue
        integration_name, version = match.groups()
        if target in EXCLUDED_INTEGRATION_VERSION or integration_name in EXCLUDED_INTEGRATIONS:
            continue
        root_layout_type = metadata["custom"]["root-layout-type"]
        assert root_layout_type in ("core", "extras")
        known_version = results[integration_name].version
        if parse_version(known_version) < parse_version(version):
            # The test only downloads the latest integrations versions.
            results[integration_name] = IntegrationMetadata(version, root_layout_type)

    return dict(results)


@pytest.mark.online
@pytest.mark.usefixtures("restore_repo_state")
def test_downloader():
    integrations_metadata = get_all_integrations_metadata()
    # Download the global simple index, which contains all known package names.
    index = urljoin(REPOSITORY_URL_PREFIX, "targets/simple/index.html")
    r = requests.get(index)
    r.raise_for_status()

    integrations_to_test = []
    for line in r.text.split("\n"):
        match = _HTML_PATTERN_RE.match(line)
        if not match:
            continue
        integration_name = match.group(1)
        if integration_name in EXCLUDED_INTEGRATIONS:
            continue
        if integration_name not in integrations_metadata:
            raise Exception(
                "Integration '{}' is in the simple index but does not have tuf metadata.".format(integration_name)
            )

        version, root_layout_type = integrations_metadata[integration_name]
        if match:
            integrations_to_test.append((match.group(1), version, root_layout_type))

    sample = random.sample(integrations_to_test, _TEST_DOWNLOADER_SAMPLE_SIZE)

    for integration_name, integration_version, root_layout_type in sample:
        _do_download(integration_name, integration_version, root_layout_type)
