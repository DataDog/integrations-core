# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from unittest import mock

import pytest

from datadog_checks.fluxcd import FluxcdCheck


@pytest.fixture(scope="session")
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {
        "openmetrics_endpoint": "http://localhost:3000/metrics",
    }


@pytest.fixture
def check(instance):
    return FluxcdCheck("gitea", {}, [instance])


@pytest.fixture()
def mock_metrics_v1():
    fixture_file = os.path.join(os.path.dirname(__file__), "fixtures", "metrics-v1.txt")

    with open(fixture_file, "r") as f:
        content = f.read()

    with mock.patch(
        "requests.get",
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: content.split("\n"),
            headers={"Content-Type": "text/plain"},
        ),
    ):
        yield


@pytest.fixture()
def mock_metrics_v2():
    fixture_file = os.path.join(os.path.dirname(__file__), "fixtures", "metrics-v2.txt")

    with open(fixture_file, "r") as f:
        content = f.read()

    with mock.patch(
        "requests.get",
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: content.split("\n"),
            headers={"Content-Type": "text/plain"},
        ),
    ):
        yield
