# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .test_metrics import (
    GAUGE_METRICS_E2E,
)


@pytest.mark.e2e
@pytest.mark.parametrize('gauge', GAUGE_METRICS_E2E)
def test_e2e_gauge_metrics(dd_agent_check, gauge):
    aggregator = dd_agent_check(rate=True)
    aggregator.assert_metric('kuma.' + gauge)
