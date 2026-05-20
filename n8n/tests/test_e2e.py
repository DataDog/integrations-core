# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable

import pytest

from datadog_checks.dev.utils import assert_service_checks

from . import common


@pytest.mark.e2e
def test_check_n8n_e2e(
    dd_agent_check: Callable[..., Any],
):
    aggregator = dd_agent_check(rate=True)

    aggregator.assert_metric('n8n.readiness.check', value=1, tags=['status_code:200', 'n8n_process:main'], at_least=1)
    # Worker also exposes /healthz/readiness via QUEUE_HEALTH_CHECK_ACTIVE on its own port.
    aggregator.assert_metric('n8n.readiness.check', value=1, tags=['status_code:200', 'n8n_process:worker'], at_least=1)

    aggregator.assert_metrics_using_metadata(
        common.get_metadata_metrics_for_version(exclude_rare=True),
        check_submission_type=True,
        check_symmetric_inclusion=True,
        exclude=list(common.RARE_EVENT_METRIC_NAMES),
    )
    assert_service_checks(aggregator)
