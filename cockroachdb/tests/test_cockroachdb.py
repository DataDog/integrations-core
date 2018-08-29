# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import itervalues

from datadog_checks.cockroachdb import CockroachdbCheck
from datadog_checks.cockroachdb.metrics import METRIC_MAP


def test_check(aggregator, instance):
    check = CockroachdbCheck('cockroachdb', {}, {}, [instance])
    check.check(instance)

    for metric in itervalues(METRIC_MAP):
        try:
            aggregator.assert_metric(metric)
        except AssertionError:
            pass

    assert aggregator.metrics_asserted_pct > 80
