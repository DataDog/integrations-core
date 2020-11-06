# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.types import ServiceCheckStatus
from datadog_checks.voltdb._types import Instance

from . import common


def assert_service_checks(aggregator, instance, connect_status=AgentCheck.OK):
    # type: (AggregatorStub, Instance, ServiceCheckStatus) -> None
    aggregator.assert_service_check('voltdb.can_connect', connect_status, count=1)


def assert_metrics(aggregator):
    # type: (AggregatorStub) -> None
    for metric in common.METRICS:
        aggregator.assert_metric(metric)  # TODO check types and tags.
    aggregator.assert_all_metrics_covered()
    # aggregator.assert_metrics_using_metadata(get_metadata_metrics())  # TODO
