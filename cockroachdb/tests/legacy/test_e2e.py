# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .common import assert_check


def test_e2e(dd_agent_check, instance_legacy):
    aggregator = dd_agent_check(instance_legacy, rate=True)
    assert_check(aggregator)
