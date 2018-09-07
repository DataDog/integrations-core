# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.pivotal_pks import PivotalPksCheck


def test_check(aggregator, instance):
    check = PivotalPksCheck('pivotal_pks', {}, {})
    check.check(instance)

    aggregator.assert_all_metrics_covered()
