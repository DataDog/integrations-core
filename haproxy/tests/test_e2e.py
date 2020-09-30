# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from . import common

pytestmark = [common.requires_new_environment, pytest.mark.e2e]


def test_check(dd_agent_check, prometheus_metrics):
    aggregator = dd_agent_check(common.INSTANCE, rate=True)

    for metric in prometheus_metrics:
        aggregator.assert_metric('haproxy.{}'.format(metric))

    aggregator.assert_all_metrics_covered()
