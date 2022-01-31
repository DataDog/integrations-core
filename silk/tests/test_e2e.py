# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.silk import SilkCheck

from .common import BLOCKSIZE_METRICS, METRICS, READ_WRITE_METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)
    for metric in METRICS:
        aggregator.assert_metric(metric)

    # blocksize and read/write metrics don't appear in test env since caddy can't mock HTTP query strings
    for metric in BLOCKSIZE_METRICS + READ_WRITE_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_service_check('silk.can_connect', SilkCheck.OK)
    aggregator.assert_service_check('silk.system.state', SilkCheck.OK)
    aggregator.assert_service_check('silk.server.state', SilkCheck.OK, count=2)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
