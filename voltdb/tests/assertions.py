# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.types import ServiceCheckStatus
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.voltdb.types import Instance

from . import common


def assert_service_checks(aggregator, instance, connect_status=AgentCheck.OK, tags=None):
    # type: (AggregatorStub, Instance, ServiceCheckStatus, List[str]) -> None
    tags = common.SERVICE_CHECK_TAGS if tags is None else tags
    aggregator.assert_service_check('voltdb.can_connect', connect_status, count=1, tags=tags + common.COMMON_TAGS)


def assert_metrics(aggregator):
    # type: (AggregatorStub) -> None
    for metric_names, tagnames in common.METRICS:
        for metric_name in metric_names:
            aggregator.assert_metric(metric_name)
            for m in aggregator.metrics(metric_name):
                metric_tagnames = {tag.split(':')[0] for tag in set(m.tags + common.COMMON_TAGS)}
                assert set(tagnames) <= set(metric_tagnames)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=common.METADATA_EXCLUDE_METRICS)
