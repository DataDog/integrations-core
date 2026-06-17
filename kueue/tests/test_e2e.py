# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import EXPECTED_METRIC_TAGS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)

    for metric, tags in EXPECTED_METRIC_TAGS.items():
        aggregator.assert_metric(metric, at_least=1)
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)
