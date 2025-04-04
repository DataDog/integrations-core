# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import AgentCheck


class TestAssertMetric:

    def test_assert_metric_hostname(self, aggregator):
        check = AgentCheck()

        check.gauge('test.metric', 1, hostname=None)
        check.gauge('test.metric_host', 1, hostname='hello')

        aggregator.assert_metric('test.metric', 1, hostname='')
        aggregator.assert_metric('test.metric_host', 1, hostname='hello')
