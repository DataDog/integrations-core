# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest


def pytest_addoption(parser):
    """Make sure the online part of the testsuite is parametrizable."""
    parser.addoption(
        "--distribution-name",
        action="store",
        default="datadog-active-directory",
        help="Standard distribution name of the desired Datadog check.",
    )
    parser.addoption(
        "--distribution-version",
        action="store",
        default="1.10.0",
        help="The version number of the desired Datadog check.",
    )
    parser.addoption(
        "--verify-all-integrations",
        action="store_true",
        help="Verify all Datadog integrations.",
    )


@pytest.fixture
def verify_all_integrations(request):
    """Provide verify_all fixture."""
    return request.config.getoption("--verify-all-integrations")


@pytest.fixture
def distribution_name(request):
    """Provide distribution_name fixture."""
    return request.config.getoption("--distribution-name")


@pytest.fixture
def distribution_version(request):
    """Provide distribution_version fixture."""
    return request.config.getoption("--distribution-version")


def pytest_configure(config):
    config.addinivalue_line("markers", "online: a test uses S3 to obtain targets, intoto and tuf metadata")
    config.addinivalue_line("markers", "offline: a test uses local targets, intoto and tuf metadata")
