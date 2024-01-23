# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from . import common


@pytest.mark.e2e
def test_check_ok(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    metrics = common.FORMATTED_EXTRA_METRICS

    for metric in metrics:
        aggregator.assert_metric(
            metric,
            at_least=0 if metric in common.OPTIONAL_METRICS else 1,
        )

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
