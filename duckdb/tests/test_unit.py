# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.duckdb import DuckdbCheck

from . import common


def test_check(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    instance = common.DEFAULT_INSTANCE
    check = DuckdbCheck('duckdb', {}, [instance])
    dd_run_check(check)

    aggregator.assert_service_check('duckdb.can_connect', DuckdbCheck.OK)
    #aggregator.assert_service_check('duckdb.can_query', DuckdbCheck.OK)

    for metric in common.METRICS_MAP:
        aggregator.assert_metric(metric)

def test_version(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    instance = common.DEFAULT_INSTANCE
    check = DuckdbCheck('duckdb', {}, [instance])
    dd_run_check(check)

    aggregator.assert_service_check('duckdb.can_connect', DuckdbCheck.OK)


def test_database_connection(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    instance = common.DEFAULT_INSTANCE
    check = DuckdbCheck('duckdb', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('duckdb.can_connect', DuckdbCheck.OK)
