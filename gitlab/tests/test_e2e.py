# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import ALLOWED_METRICS, METRICS_TO_TEST, METRICS_TO_TEST_V2, assert_check

pytestmark = pytest.mark.e2e


def test_e2e_legacy(dd_agent_check, legacy_config):
    aggregator = dd_agent_check(legacy_config, rate=True)
    assert_check(aggregator, ALLOWED_METRICS)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize('use_openmetrics', [True, False], indirect=True)
def test_e2e(dd_agent_check, config, use_openmetrics):
    if use_openmetrics:
        instance = config['instances'][0]
        instance["openmetrics_endpoint"] = instance["prometheus_url"]

    aggregator = dd_agent_check(config, rate=True)
    assert_check(aggregator, METRICS_TO_TEST_V2 if use_openmetrics else METRICS_TO_TEST, use_openmetrics)
    # Excluding gitlab.rack.http_requests_total because it is a distribution metric
    # (its sum and count metrics are in the metadata)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=["gitlab.rack.http_requests_total"])
