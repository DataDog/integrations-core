# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import logging
from datetime import datetime, timezone
from typing import Any

from bson import json_util
from mock import MagicMock

from datadog_checks.mongo.dbm.slow_operations import MongoSlowOperations

# MongoDB 8.0 RSM topology change log with Int64.MIN_VALUE as a $date sentinel
# for "never updated" in the ReplicaSetMonitor.
RSM_TOPOLOGY_CHANGE_LOG = json.dumps(
    {
        "t": {"$date": "2024-06-01T12:00:00.500+00:00"},
        "s": "I",
        "c": "NETWORK",
        "id": 4333213,
        "ctx": "ReplicaSetMonitor-TaskExecutor",
        "msg": "RSM Topology Change",
        "attr": {
            "replicaSet": "rs0",
            "newDescription": {
                "topologyType": "ReplicaSetWithPrimary",
                "servers": [
                    {
                        "address": "mongodb-dev1:27017",
                        "type": "RSPrimary",
                        "lastUpdateTime": {"$date": {"$numberLong": "-9223372036854775808"}},
                        "roundTripTime": {"$numberLong": "1234"},
                    }
                ],
            },
        },
    }
)

SLOW_QUERY_LOG_TEMPLATE = (
    '{{"t":{{"$date":"{timestamp}"}},'
    '"s":"I","c":"COMMAND","id":51803,"ctx":"conn50","msg":"Slow query",'
    '"attr":{{"type":"command","ns":"test.$cmd",'
    '"command":{{"update":"customers","ordered":true,"$db":"test"}},'
    '"numYields":0,"reslen":60,"durationMillis":11}}}}'
)

MOCK_SLOW_OPS_CONFIG = {
    'enabled': True,
    'collection_interval': 10,
    'max_operations': 100,
    'explain_verbosity': 'queryPlanner',
    'explained_operations_cache_maxsize': 5000,
    'explained_operations_per_hour_per_query': 10,
    'run_sync': True,
}


def _make_slow_query_log(timestamp: str) -> str:
    return SLOW_QUERY_LOG_TEMPLATE.format(timestamp=timestamp)


def _make_mock_check():
    check = MagicMock()
    check._config.slow_operations = MOCK_SLOW_OPS_CONFIG
    check._config.timeout = 10000
    check._config.min_collection_interval = 15
    check._database_autodiscovery._max_databases = 100
    check.log = logging.getLogger('test_slow_operations')
    return check


class TestSlowOperationsRSMTopologyOverflow:
    """Regression: out-of-range $date values in MongoDB 8.0 RSM topology logs
    must not break log parsing or degrade binary search."""

    def test_json_parse_rsm_topology_change_log(self):
        """json_util.loads must handle out-of-range $date sentinels without raising."""
        slow_ops = MongoSlowOperations(_make_mock_check())
        parsed = json_util.loads(RSM_TOPOLOGY_CHANGE_LOG, json_options=slow_ops._log_json_opts)
        assert parsed["msg"] == "RSM Topology Change"

    def test_binary_search_with_rsm_topology_log_in_middle(self):
        """_binary_search must complete correctly when an RSM topology entry is at the midpoint."""
        slow_ops = MongoSlowOperations(_make_mock_check())

        logs = [
            _make_slow_query_log("2024-06-01T11:00:00.000+00:00"),
            _make_slow_query_log("2024-06-01T11:30:00.000+00:00"),
            RSM_TOPOLOGY_CHANGE_LOG,
            _make_slow_query_log("2024-06-01T12:30:00.000+00:00"),
            _make_slow_query_log("2024-06-01T13:00:00.000+00:00"),
        ]

        target_ts = datetime(2024, 6, 1, 12, 15, 0, tzinfo=timezone.utc).timestamp()
        result = slow_ops._binary_search(logs, target_ts)
        assert result >= 3, f"_binary_search returned {result}, expected >= 3 (bailed out early)"

    def test_collect_slow_operations_skips_rsm_topology_without_error(self):
        """RSM topology entries must be skipped via the msg filter, not via exception handling."""
        check = MagicMock()
        check._config.slow_operations = MOCK_SLOW_OPS_CONFIG
        check._config.timeout = 10000
        check._config.min_collection_interval = 15
        check._database_autodiscovery._max_databases = 100

        slow_ops = MongoSlowOperations(check)
        check.api_client.get_log_data.return_value = {
            "log": [
                RSM_TOPOLOGY_CHANGE_LOG,
                _make_slow_query_log("2024-06-01T13:00:00.000+00:00"),
            ]
        }

        last_ts = datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc).timestamp()
        results = list[Any](slow_ops._collect_slow_operations_from_logs({"test"}, last_ts))
        assert len(results) == 1
        check.log.error.assert_not_called()
