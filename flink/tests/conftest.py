# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
from unittest import mock

import pytest

from datadog_checks.flink import FlinkCheck

INSTANCE = {
    "openmetrics_endpoint": "http://localhost:9249/metrics",
}


@pytest.fixture
def instance():
    return copy.deepcopy(INSTANCE)


@pytest.fixture
def check(instance):
    return FlinkCheck('flink', {}, [instance])


@pytest.fixture()
def mock_metrics():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.Session.get',
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={'Content-Type': "text/plain"},
        ),
    ):
        yield
