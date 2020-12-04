# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.glusterfs import GlusterfsCheck

from .common import EXPECTED_METRICS

INIT_CONFIG = {'gstatus_path': '/usr/local/bin/gstatus'}


def test_check(aggregator, instance, mock_gstatus_data):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = GlusterfsCheck('glusterfs', INIT_CONFIG, [instance])
    check.check(instance)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
