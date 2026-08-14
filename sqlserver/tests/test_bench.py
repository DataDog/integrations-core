# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.sqlserver.const import INSTANCE_METRICS, INSTANCE_METRICS_DATABASE
from datadog_checks.sqlserver.metrics import SqlSimpleMetric

# Databases on the server that are always present, plus the aggregate instance the DMV reports.
SERVER_DATABASES = ['master', 'tempdb', 'msdb', 'model', '_Total']

# The name columns of sys.dm_os_performance_counters are nchar(128), so values come back blank-padded.
COUNTER_NAME_WIDTH = 128

# A real logger rather than a mock: mocks record every call, which would accumulate across benchmark
# rounds and distort both the timing and the memory profile.
benchmark_logger = logging.getLogger(__name__)
benchmark_logger.addHandler(logging.NullHandler())
benchmark_logger.setLevel(logging.WARNING)


class StubCursor:
    """Returns a fixed result set, standing in for the cursor `fetch_all_values` queries."""

    description = [('counter_name',), ('instance_name',), ('object_name',), ('cntr_value',)]

    def __init__(self, rows):
        self._rows = rows

    def execute(self, *args, **kwargs):
        pass

    def fetchall(self):
        return self._rows


def _discard_metric(*args, **kwargs):
    pass


def _row(counter_name, instance_name, object_name, cntr_value):
    return (
        counter_name.ljust(COUNTER_NAME_WIDTH),
        instance_name.ljust(COUNTER_NAME_WIDTH),
        object_name.ljust(COUNTER_NAME_WIDTH),
        cntr_value,
    )


def _build_dispatch_inputs(num_databases):
    """Build the metric objects and result set the check would hold for `num_databases` databases.

    Mirrors `_add_performance_counters`: instance-level counters once, then the database-scoped
    counters once per autodiscovered database. Every counter is treated as a simple metric so the
    benchmark isolates the `SqlSimpleMetric` dispatch.
    """
    databases = ['tenant_db_{:04d}'.format(i) for i in range(num_databases)]
    base_tags = ['database_hostname:sql-1', 'database_instance:sql-1', 'port:1433']

    metrics = []
    for name, counter_name, instance_name, object_name in INSTANCE_METRICS:
        metrics.append(
            SqlSimpleMetric(
                {
                    'name': name,
                    'counter_name': counter_name,
                    'instance_name': instance_name,
                    'object_name': object_name,
                    'tags': base_tags,
                },
                None,
                _discard_metric,
                None,
                benchmark_logger,
            )
        )
    for database in databases:
        database_tags = base_tags + ['database:{}'.format(database)]
        for name, counter_name, _, object_name in INSTANCE_METRICS_DATABASE:
            metrics.append(
                SqlSimpleMetric(
                    {
                        'name': name,
                        'counter_name': counter_name,
                        'instance_name': database,
                        'object_name': object_name,
                        'physical_db_name': database,
                        'tags': database_tags,
                    },
                    None,
                    _discard_metric,
                    None,
                    benchmark_logger,
                )
            )

    # The query filters on counter name only, so database-scoped counters return a row for every
    # database on the server regardless of which ones autodiscovery selected.
    rows = [
        _row(counter_name, instance_name, object_name or 'SQLServer:Generic', 1)
        for _, counter_name, instance_name, object_name in INSTANCE_METRICS
    ]
    for _, counter_name, _, object_name in INSTANCE_METRICS_DATABASE:
        rows.extend(
            _row(counter_name, database, object_name or 'SQLServer:Databases', 1)
            for database in databases + SERVER_DATABASES
        )

    counter_names = sorted({counter_name for _, counter_name, _, _ in INSTANCE_METRICS + INSTANCE_METRICS_DATABASE})
    return metrics, rows, counter_names


@pytest.mark.parametrize('num_databases', [50, 100, 250, 500])
def test_simple_metric_dispatch(benchmark, num_databases):
    """Time one check run's worth of perf-counter dispatch as the database count grows.

    Both the number of metric objects and the number of rows scale with the database count, so this
    is where a per-metric scan of the full result set becomes quadratic. Compare the growth across
    the parameters rather than absolute times.
    """
    metrics, rows, counter_names = _build_dispatch_inputs(num_databases)

    def dispatch():
        results, columns = SqlSimpleMetric.fetch_all_values(StubCursor(rows), counter_names, benchmark_logger)
        for metric in metrics:
            metric.fetch_metric(results, columns)

    benchmark(dispatch)
