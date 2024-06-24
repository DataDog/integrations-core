# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.utils import assert_service_checks


def test_kyverno_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    assert_service_checks(aggregator)
