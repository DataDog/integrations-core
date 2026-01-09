# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.utils import assert_service_checks


def test_check_n8n_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    # Assert the readiness check metric is present with status_code tag
    aggregator.assert_metric('n8n.readiness.check', value=1, tags=["status_code:200"], at_least=1)

    assert_service_checks(aggregator)
