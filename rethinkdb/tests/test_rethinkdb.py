# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.rethinkdb import RethinkdbCheck


def test_check(aggregator, instance):
    check = RethinkdbCheck('rethinkdb', {}, {})
    check.check(instance)

    aggregator.assert_all_metrics_covered()
