# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.cloud_foundry_api import CloudFoundryApiCheck


def test_check(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
    check.check(instance)

    aggregator.assert_all_metrics_covered()
