# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.linkerd2 import Linkerd2Check


def test_check(aggregator, instance):
    check = Linkerd2Check('linkerd2', {}, {})
    check.check(instance)

    aggregator.assert_all_metrics_covered()
