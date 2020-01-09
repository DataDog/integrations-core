# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.ibm_db2 import IbmDb2Check

from . import metrics


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_standard(aggregator, instance):
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.check(instance)

    _assert_standard(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    _assert_standard(aggregator)


def _assert_standard(aggregator):
    aggregator.assert_service_check('ibm_db2.can_connect', AgentCheck.OK)

    for metric in metrics.STANDARD:
        aggregator.assert_metric_has_tag(metric, 'db:datadog')
        aggregator.assert_metric_has_tag(metric, 'foo:bar')
    aggregator.assert_all_metrics_covered()
