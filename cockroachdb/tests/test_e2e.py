# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .common import assert_metrics


def test_metrics(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    assert_metrics(aggregator)
