# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import platform

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import METRICS, METRICS_V2


@pytest.mark.e2e
def test_check_ok(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


@pytest.mark.skipif(platform.python_version() < "3", reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.e2e
def test_check_ok_omv2(dd_agent_check, omv2_instance):
    aggregator = dd_agent_check(omv2_instance, rate=True)
    for metric in METRICS_V2:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
