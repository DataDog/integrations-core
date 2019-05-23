# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.harbor import HarborCheck


def test_check(aggregator, instance):
    check = HarborCheck('harbor', {}, {})
    check.check(instance)

    aggregator.assert_all_metrics_covered()
