# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.nutanix import NutanixCheck

pytestmark = [
    pytest.mark.integration,
]


def test_connect_ok(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_connect_error(dd_run_check, aggregator, aws_instance):
    with pytest.raises(Exception):
        check = NutanixCheck('nutanix', {}, [{}])
        dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=0, count=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
