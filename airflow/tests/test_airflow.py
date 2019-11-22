# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.airflow import AirflowCheck


def test_check(aggregator, instance):
    check = AirflowCheck('airflow', {}, {})
    check.check(instance)

    aggregator.assert_all_metrics_covered()
