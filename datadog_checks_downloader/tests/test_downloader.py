# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import glob
import logging
import os
import random
import re
import shutil
import string
import subprocess
import sys
import time
from collections import defaultdict, namedtuple
from datetime import datetime

import pytest
import requests
from packaging.version import parse as parse_version
from six import PY2, PY3, iteritems
from six.moves.urllib_parse import urljoin
from tenacity import retry, stop_after_attempt, wait_exponential
from tests.local_http import local_http_server, local_http_server_local_dir
from tuf.exceptions import NoWorkingMirrorError

import datadog_checks.downloader
from datadog_checks.downloader.cli import download
from datadog_checks.downloader.download import REPOSITORY_URL_PREFIX
from datadog_checks.downloader.exceptions import NonDatadogPackage

if PY3:
    from unittest import mock
else:
    from mock import mock

_LOGGER = logging.getLogger("test_downloader")

# Preserve datetime to make sure tests that use local metadata do not expire.
_LOCAL_TESTS_DATA_TIMESTAMP = time.mktime(datetime(year=2022, month=7, day=25).timetuple())

# Used to test local metadata expiration.
_LOCAL_TESTS_DATA_TIMESTAMP_EXPIRED = time.mktime(datetime(year=2522, month=1, day=1).timetuple())

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


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the downloader's cache to make sure it does not affect test results."""
    # current
    metadata_current_dir = os.path.join(
        os.path.dirname(datadog_checks.downloader.__file__),
        "data",
        "repo",
        "metadata",
        "current",
    )
    for file_ in os.listdir(metadata_current_dir):
        if file_ == "root.json" or file_.startswith("."):
            continue

        file_path = os.path.join(metadata_current_dir, file_)

        if not os.path.isfile(file_path):
            # Skip any nested dirs.
            continue

        os.remove(file_path)

    # previous
    metadata_previous_dir = os.path.join(
        os.path.dirname(datadog_checks.downloader.__file__),
        "data",
        "repo",
        "metadata",
        "previous",
    )
    for file_ in os.listdir(metadata_previous_dir):
        if file_.startswith("."):
            continue

        file_path = os.path.join(metadata_previous_dir, file_)

        if not os.path.isfile(file_path):
            # Skip any nested dirs.
            continue

        os.remove(file_path)

    # targets
    targets_dir = os.path.join(os.path.dirname(datadog_checks.downloader.__file__), "data", "repo", "targets")
    for item in os.listdir(targets_dir):
        if item.startswith("."):
            continue

        shutil.rmtree(os.path.join(targets_dir, item))


def _do_run_downloader(argv):
    """Run the Datadog checks downloader."""
    old_sys_argv = sys.argv

    sys.argv = ["datadog_checks_downloader"] + argv  # Make sure argv[0] (program name) is prepended.
    try:
        download()
    finally:
        sys.args = old_sys_argv


@pytest.mark.online
def test_download(capfd, distribution_name, distribution_version):
    """Test datadog-checks-downloader successfully downloads and validates a wheel file."""
    argv = [distribution_name, "--version", distribution_version]

    _do_run_downloader(argv)
    stdout, stderr = capfd.readouterr()

    assert not stderr, "No standard error expected, got: {}".format(stderr)

    output = [line for line in stdout.splitlines() if line]
    assert len(output) == 1, "Only one output line expected, got {}:\n\t{}".format(len(output), stdout)

    # XXX: could be extended to be less error-prone.
    delimiter = "datadog_checks_downloader/datadog_checks/downloader/data/repo/targets/" "simple/{}/{}-{}".format(
        distribution_name, distribution_name.replace("-", "_"), distribution_version
    )

    parts = output[0].split(delimiter)

    assert len(parts) == 2, "Unable to find expected substring {} in {}".format(delimiter, output[0])
    assert parts[1].endswith(".whl"), "No wheel extension found in {}".format(parts[1])


@pytest.mark.online
@pytest.mark.skipif(PY2, reason="tuf builds for Python 2 do not provide required information in exception")
def test_expired_metadata_error(distribution_name, distribution_version):
    """Test expiration of metadata raises an exception."""
    argv = [distribution_name, "--version", distribution_version]

    # Make sure time.time returns futuristic time.
    with mock.patch(
        "time.time",
        mock.MagicMock(return_value=time.mktime(datetime(year=2524, month=1, day=1).timetuple())),
    ), pytest.raises(NoWorkingMirrorError) as exc:
        _do_run_downloader(argv)

    # No exception chaining done, make a check to see ExpiredMetadataError in the exception string.
    assert "ExpiredMetadataError(\"Metadata 'timestamp' expired on" in str(exc)


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
            "datadog_checks_downloader/datadog_checks/downloader/data/repo/targets/"
            "simple/datadog-active-directory/datadog_active_directory-1.10.0-py2.py3-none-any.whl",
        ),
    ],
)
@pytest.mark.skipif(PY2, reason="tuf builds for Python 2 do not provide required information in exception")
@mock.patch("time.time", mock.MagicMock(return_value=_LOCAL_TESTS_DATA_TIMESTAMP))
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
@pytest.mark.skipif(PY2, reason="tuf builds for Python 2 do not provide required information in exception")
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

        # Make sure time.time returns futuristic time.
        with mock.patch(
            "time.time",
            mock.MagicMock(return_value=_LOCAL_TESTS_DATA_TIMESTAMP_EXPIRED),
        ), pytest.raises(NoWorkingMirrorError) as exc:
            _do_run_downloader(argv)

        # No exception chaining done, make a check to see ExpiredMetadataError in the exception string.
        assert "ExpiredMetadataError(\"Metadata 'timestamp' expired on" in str(exc)


@pytest.mark.offline
@pytest.mark.skipif(PY2, reason="tuf builds for Python 2 do not provide required information in exception")
def test_local_unreachable_repository():
    """Test unreachable repository raises an exception."""
    argv = [
        "datadog-some-distribution",
        "--version",
        "1.0.0",
        "--repository",
        "http://localhost:1",
    ]

    with pytest.raises(NoWorkingMirrorError) as exc:
        _do_run_downloader(argv)

    # No exception chaining done, check the exception content.
    assert "ConnectionError(MaxRetryError(" in str(exc)


@pytest.mark.offline
@pytest.mark.skipif(PY2, reason="tuf builds for Python 2 do not provide required information in exception")
def test_local_repository_empty():
    """Test unreachable repository raises an exception."""
    with local_http_server("empty") as http_url:
        argv = [
            "datadog-active-directory",
            "--version",
            "1.10.0",
            "--repository",
            http_url,
        ]

        with pytest.raises(NoWorkingMirrorError) as exc:
            _do_run_downloader(argv)

        assert "HTTPError('404 Client Error: File not found for url" in str(exc)


@pytest.mark.offline
@pytest.mark.parametrize(
    "distribution_name,distribution_version",
    [
        ("datadog-active-directory", "1.10.0"),
    ],
)
@pytest.mark.skipif(PY2, reason="tuf builds for Python 2 do not provide required information in exception")
@mock.patch("time.time", mock.MagicMock(return_value=_LOCAL_TESTS_DATA_TIMESTAMP))
def test_local_wheels_signer_signature_leaf_error(distribution_name, distribution_version):
    """Test failure in verifying wheels-signer signature.

    The wheel-signer-{a-z} metadata has to have wrong signature.
    """
    test_data = "{}-{}-signature-wheels-signer-a".format(distribution_name, distribution_version)
    with local_http_server(test_data) as http_url:
        argv = [
            distribution_name,
            "--version",
            distribution_version,
            "--repository",
            http_url,
        ]

        with pytest.raises(NoWorkingMirrorError) as exc:
            _do_run_downloader(argv)

    assert "BadSignatureError('wheels-signer-" in str(exc)


def delete_files(files):
    for f in files:
        os.remove(f)


def _cleanup():
    REPO_DIR = "datadog_checks/downloader/data/repo/"

    METADATA_DIR = os.path.join(REPO_DIR, "metadata")
    TARGETS_DIR = os.path.join(REPO_DIR, "targets")
    IN_TOTO_METADATA_DIR = os.path.join(TARGETS_DIR, "in-toto-metadata")
    IN_TOTO_PUBKEYS_DIR = os.path.join(TARGETS_DIR, "in-toto-pubkeys")
    SIMPLE_DIR = os.path.join(TARGETS_DIR, "simple")

    # First, nuke all known targets. but not the directory for targets itself.
    shutil.rmtree(IN_TOTO_METADATA_DIR, ignore_errors=True)
    shutil.rmtree(IN_TOTO_PUBKEYS_DIR, ignore_errors=True)
    shutil.rmtree(SIMPLE_DIR, ignore_errors=True)

    # Then, nuke all previous TUF metadata.
    previous_jsons = os.path.join(METADATA_DIR, "previous/*.json")
    previous_jsons = glob.glob(previous_jsons)
    delete_files(previous_jsons)

    # Finally, nuke ALL current TUF metadata EXCEPT the unversioned root metadata.
    current_jsons = os.path.join(METADATA_DIR, "current/*.json")
    current_jsons = glob.glob(current_jsons)
    current_jsons = [c for c in current_jsons if os.path.basename(c) != "root.json"]
    delete_files(current_jsons)


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
        "python",
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
    for target, metadata in iteritems(targets):
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
    try:
        for integration_name, integration_version, root_layout_type in sample:
            _do_download(integration_name, integration_version, root_layout_type)
    finally:
        _cleanup()
