# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.fly_io import FlyIoCheck

from .common import MOCKED_METRICS
from .conftest import HERE


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


def test_check(dd_run_check, aggregator, instance, mock_http_response, caplog):
    mock_http_response(file_path=get_fixture_path('output.txt'))

    check = FlyIoCheck('fly_io', {}, [instance])

    dd_run_check(check)
    for metric in MOCKED_METRICS:
        aggregator.assert_metric(metric, at_least=1, hostname="708725eaa12297")
        aggregator.assert_metric(metric, at_least=1, hostname="20976671ha2292")
        aggregator.assert_metric(metric, at_least=1, hostname="119dc024cbf534")

    aggregator.assert_all_metrics_covered()
