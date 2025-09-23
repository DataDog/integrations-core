# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import contextlib
import decimal
import os
from enum import Enum
from ipaddress import IPv4Address

import orjson
import psycopg
import pytest
from psycopg import Connection, Cursor

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.stubs.common import MetricStub
from datadog_checks.postgres.connection_pool import LRUConnectionPoolManager

from .conftest import SnapshotMode


class Observer:
    def __getattr__(self, attr):
        if attr not in self.__dict__:
            if self.target:
                return getattr(self.target, attr)
            return None
        return super().__getattr__(attr)


class PoolObserver(Observer):
    mode = "record"

    def __init__(self, pool_manager: LRUConnectionPoolManager, *args, **kwargs):
        self.snapshot = []
        self.target = pool_manager

    def get_connection(self, dbname: str, persistent: bool = False):
        conn = self.target.get_connection(dbname, persistent)
        return ConnectionObserver(conn, self.snapshot, self.mode)


class ConnectionObserver(Observer):
    def __init__(self, conn: Connection, snapshot: list, mode: str):
        # print(f"Initializing connection observer")
        self.snapshot = snapshot
        self.target = conn
        self.mode = mode

    @contextlib.contextmanager
    def cursor(self, *args, **kwargs):
        # print(f"Getting cursor")
        if self.mode == "record":
            yield CursorObserver(self.target.cursor(*args, **kwargs), self.snapshot, self.mode)
        if self.mode == "replay":
            yield CursorObserver(None, self.snapshot, self.mode)
        # raise ValueError(f"Mode {self.mode} is not supported")

    @property
    def info(self):
        if self.target:
            return self.target.info

        # Replay connection is always OK
        class Info:
            status = psycopg.pq.ConnStatus.OK
            dbname = "replay"

        return Info()


# Mark as contextmanagers because the underlying cursor is a contextmanager
# @contextlib.contextmanager
replay_offset = 0


class CursorObserver(Observer):
    def __init__(self, cursor: Cursor, snapshot: list, mode: str):
        # print(f"Initializing cursor observer {cursor}")
        self.target = cursor
        self.snapshot = snapshot
        self.mode = mode

    def execute(self, query, *args, **kwargs):
        global replay_offset
        # print("executing query", query, self.mode)
        if self.mode == SnapshotMode.RECORD:
            self.snapshot.append(query)
            return self.target.execute(query, *args, **kwargs)
        if self.mode == SnapshotMode.REPLAY:
            # Check that the top of the snapshot is the same as the query
            if self.snapshot[replay_offset] != query:
                print("Query does not match snapshot", query, self.snapshot[replay_offset])
                raise ValueError(f"Query {query} does not match snapshot {self.snapshot[replay_offset]}")
            # print("Query matches snapshot", query, self.snapshot[replay_offset])
            replay_offset += 1
            return

        raise ValueError(f"Mode {self.mode} is not supported")

    def fetchone(self):
        if self.mode == SnapshotMode.RECORD:
            result = self.target.fetchone()
            self.snapshot.append(result)
            return result
        if self.mode == SnapshotMode.REPLAY:
            return self.replay()
        raise ValueError(f"Mode {self.mode} is not supported")

    def fetchall(self):
        if self.mode == SnapshotMode.RECORD:
            result = self.target.fetchall()
            self.snapshot.append(result)
            return result
        if self.mode == SnapshotMode.REPLAY:
            return self.replay()
        raise ValueError(f"Mode {self.mode} is not supported")

    def replay(self):
        global replay_offset
        # print("Replaying value", self.snapshot[replay_offset])
        if self.snapshot[replay_offset] and not isinstance(self.snapshot[replay_offset], list):
            print("Snapshot is not a list", self.snapshot[replay_offset])
            raise ValueError(f"Snapshot {self.snapshot[replay_offset]} is not a list")
        value = self.snapshot[replay_offset]
        replay_offset += 1
        return value


@pytest.mark.snapshot
def test_snapshot(aggregator: AggregatorStub, integration_check, pg_instance, snapshot_mode: SnapshotMode):
    check = integration_check(pg_instance)

    observer = PoolObserver(check.db_pool)
    observer.mode = snapshot_mode
    observer.snapshot = []

    if snapshot_mode == SnapshotMode.REPLAY:
        with open(file_path(SnapshotFileType.REQUESTS), "r") as f:
            observer.snapshot = orjson.loads(f.read())
            assert observer.snapshot != []

    def generate_new_connection(new_connection):
        def observed_new_connection(dbname):
            try:
                if observer.mode == SnapshotMode.REPLAY:
                    return ConnectionObserver(None, observer.snapshot, observer.mode)
                conn = new_connection(dbname)
            except Exception as e:
                raise e
            return ConnectionObserver(conn, observer.snapshot, observer.mode)

        return observed_new_connection

    check._new_connection = generate_new_connection(check._new_connection)
    check.db_pool = observer
    check.run()

    # Sanity check that the check ran
    aggregator.assert_metric("postgresql.running", count=1)

    output = serialize_aggregator(aggregator)

    if observer.mode == SnapshotMode.RECORD:
        with open(file_path(SnapshotFileType.REQUESTS), "w") as f:
            f.write(orjson.dumps(observer.snapshot, default=default, option=orjson.OPT_INDENT_2).decode("utf-8"))
        with open(file_path(SnapshotFileType.EXPECTED), "w") as f:
            f.write(orjson.dumps(output, default=default, option=orjson.OPT_INDENT_2).decode("utf-8"))
    elif observer.mode == SnapshotMode.REPLAY:
        with open(file_path(SnapshotFileType.EXPECTED), "r") as f:
            expected = orjson.loads(f.read())
        with open(file_path(SnapshotFileType.OUTPUT), "w") as f:
            f.write(orjson.dumps(output, default=default, option=orjson.OPT_INDENT_2).decode("utf-8"))
        assert output == expected


# def AggregatorOutput(TypedDict):
#     metrics: dict[str, list[dict]]
#     events: list[dict]


class SnapshotFileType(Enum):
    REQUESTS = "requests"
    EXPECTED = "expected"
    OUTPUT = "output"


def file_path(file_type: SnapshotFileType):
    snapshots_dir = os.path.join(os.path.dirname(__file__), "snapshots")

    test_env = os.environ.get("HATCH_ENV_ACTIVE")
    active_test = os.environ.get("PYTEST_CURRENT_TEST").replace("tests/", "").replace(":", "_").replace(".", "_")
    file_prefix = f"{test_env}.{active_test}"

    return os.path.join(snapshots_dir, f"{file_prefix}.{file_type.value}.json")


def serialize_aggregator(aggregator: AggregatorStub):
    return {
        "metrics": {name: [default(m) for m in list(aggregator.metrics(name))] for name in aggregator.metric_names},
        "events": aggregator.events,
    }


def default(obj):
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    if isinstance(obj, IPv4Address):
        return str(obj)
    if isinstance(obj, MetricStub):
        return {
            "name": obj.name,
            "type": obj.type,
            # The operation time is wall time of the running integration so will vary each time
            "value": obj.value if obj.name != "dd.postgres.operation.time" else 1,
            "tags": sorted(obj.tags),
            "hostname": obj.hostname,
            "device": obj.device,
            "flush_first_value": obj.flush_first_value,
        }
    raise TypeError
