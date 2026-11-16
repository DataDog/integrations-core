# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import CORE_METRICS, PROVIDER_METRICS

pytestmark = [pytest.mark.e2e]


def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    for endpoint, metrics in (('core', CORE_METRICS), ('provider', PROVIDER_METRICS)):
        for metric in metrics:
            aggregator.assert_metric_has_tag(metric, f'crossplane_endpoint:{endpoint}')
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
