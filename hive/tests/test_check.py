# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest


@pytest.mark.e2e
def test(dd_agent_check):
    aggregator = dd_agent_check()
    metrics = [
        "hive.server.memory.heap.committed",
        "hive.server.memory.heap.init",
        "hive.server.memory.heap.max",
        "hive.server.memory.heap.used",
        "hive.server.memory.non_heap.committed",
        "hive.server.memory.non_heap.init",
        "hive.server.memory.non_heap.max",
        "hive.server.memory.non_heap.used",
        "hive.server.memory.total.committed",
        "hive.server.memory.total.init",
        "hive.server.memory.total.max",
        "hive.server.memory.total.used",
        "hive.server.session.active",
        "hive.server.session.open",
        "hive.metastore.api.get_all_tables.active_call",
        "hive.metastore.api.get_all_functions.active_call",
        "hive.metastore.open_connections",
        "hive.metastore.partition.init",
        "hive.metastore.api.get_all_databases.active_call",
        "hive.metastore.api.init.active_call",
    ]
    for metric in metrics:
        aggregator.assert_metric(metric)
