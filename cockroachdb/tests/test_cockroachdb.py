# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import itervalues

from datadog_checks.cockroachdb import CockroachdbCheck
from datadog_checks.cockroachdb.metrics import METRIC_MAP


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_integration(aggregator, instance):
    check = CockroachdbCheck('cockroachdb', {}, {}, [instance])
    check.check(instance)

    _test_check(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)
    _test_check(aggregator)


def _test_check(aggregator):
    for metric in itervalues(METRIC_MAP):
        aggregator.assert_metric('cockroachdb.{}'.format(metric), at_least=0)

    assert aggregator.metrics_asserted_pct > 80, 'Missing metrics {}'.format(aggregator.not_asserted())
