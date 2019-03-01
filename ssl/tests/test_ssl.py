# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.ssl import SslCheck


def test_check(aggregator, instance):
    check = SslCheck('ssl', {}, {})
    check.check(instance)

    aggregator.assert_all_metrics_covered()
