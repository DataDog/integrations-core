# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [
    pytest.mark.integration,
]


def test_connect_ok(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1, count=1)


def test_connect_error(dd_run_check, aggregator, aws_instance):
    with pytest.raises(Exception):
        check = NutanixCheck('nutanix', {}, [{}])
        dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=0, count=1)


def test_cluster_metrics(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1, count=1)
    aggregator.assert_metric(
        "nutanix.clusters.count",
        value=1,
        count=1,
        tags=['nutanix_cluster_id:00063d6c-a6d6-2be8-e411-194986b149bb', 'nutanix_cluster_name:Cluster-1'],
    )

    # aggregator.assert_all_metrics_covered()
    # aggregator.assert_metrics_using_metadata(get_metadata_metrics())
