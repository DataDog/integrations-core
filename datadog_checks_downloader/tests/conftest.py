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


@pytest.fixture
def distribution_name(request):
    """Provide distribution_name fixture."""
    return request.config.getoption("--distribution-name")


@pytest.fixture
def distribution_version(request):
    """Provide distribution_version fixture."""
    return request.config.getoption("--distribution-version")
