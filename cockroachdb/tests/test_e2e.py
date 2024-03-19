# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.testing import requires_py3

from .common import assert_metrics


@requires_py3
def test_metrics(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    assert_metrics(aggregator)
