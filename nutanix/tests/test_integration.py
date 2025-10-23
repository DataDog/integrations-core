# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_health_check(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1)


def test_cluster_metrics_collection(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1)
