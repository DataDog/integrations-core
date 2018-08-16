# (C) Datadog, Inc. {year}
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.{check_name} import {check_class}


def test_check(aggregator, instance):
    check = {check_class}('{check_name}', {{}}, {{}})
    check.check(instance)

    aggregator.assert_all_metrics_covered()
