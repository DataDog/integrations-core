# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import METRICS, assert_check

pytestmark = [pytest.mark.unit]


def test_check(dd_run_check, aggregator, mock_data, gitlab_check, config):
    check = gitlab_check(config)
    dd_run_check(check)
    dd_run_check(check)

    assert_check(aggregator, METRICS)
    aggregator.assert_all_metrics_covered()
