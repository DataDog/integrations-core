# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import ALLOWED_METRICS, METRICS_TO_TEST, assert_check

pytestmark = pytest.mark.e2e


def test_e2e_legacy(dd_agent_check, legacy_config):
    aggregator = dd_agent_check(legacy_config, rate=True)
    assert_check(aggregator, ALLOWED_METRICS)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_e2e(dd_agent_check, config):
    aggregator = dd_agent_check(config, rate=True)
    assert_check(aggregator, METRICS_TO_TEST)
    # Excluding gitlab.rack.http_requests_total because it is a distribution metric
    # (its sum and count metrics are in the metadata)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=["gitlab.rack.http_requests_total"])
