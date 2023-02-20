# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.utils.platform import Platform
from datadog_checks.dev.utils import get_metadata_metrics

from . import common


@pytest.mark.e2e
def test_check_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    expected_metrics = common.E2E_EXPECTED_METRICS
    if Platform.is_windows() or Platform.is_linux():
        expected_metrics += common.EXPECTED_WINDOWS_LINUX_METRICS
    for metric in expected_metrics:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
