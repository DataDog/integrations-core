# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

from datadog_checks.azure_iot_edge import AzureIotEdgeCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics


def test_check(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = AzureIotEdgeCheck('azure_iot_edge', {}, [instance])
    check.check(instance)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
