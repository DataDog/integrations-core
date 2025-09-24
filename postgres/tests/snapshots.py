# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import contextlib
import decimal
import os
from enum import Enum
from ipaddress import IPv4Address

import orjson
import psycopg
import psycopg_binary
from psycopg import Column, Connection, Cursor

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.stubs.common import MetricStub
from datadog_checks.postgres.connection_pool import LRUConnectionPoolManager
from datadog_checks.postgres.postgres import PostgreSql

from .conftest import SnapshotMode


# File utitilies for snapshots
class SnapshotFileType(Enum):
    REQUESTS = "requests"
    EXPECTED = "expected"
    OUTPUT = "output"


def snapshot_file_path(file_type: SnapshotFileType):
    snapshots_dir = os.path.join(os.path.dirname(__file__), "snapshots")

    test_env = os.environ.get("HATCH_ENV_ACTIVE")
    # typical format of PYTEST_CURRENT_TEST is tests/test_snapshot.py::test_snapshots (call)
    # we want to format to test_snapshot.test_snapshots
    active_test = '.'.join(
        os.environ.get("PYTEST_CURRENT_TEST").split(" ")[0].replace("tests/", "").replace(".py", "").split("::")
    )
    file_prefix = f"{test_env}.{active_test}"

    return os.path.join(snapshots_dir, f"{file_prefix}.{file_type.value}.json")


def read_file(path: str, decode_json: bool = True):
    with open(path, "r") as f:
        if decode_json:
            return orjson.loads(f.read())
        return f.read()


def write_file(content, path: str):
    with open(path, "w") as f:
        f.write(orjson.dumps(content, default=default, option=orjson.OPT_INDENT_2).decode("utf-8"))


# Serialization
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
    if isinstance(obj, Column):
        return {
            "name": obj.name,
            "type_code": obj.type_code,
            "display_size": obj.display_size,
            "internal_size": obj.internal_size,
            "precision": obj.precision,
            "scale": obj.scale,
            "null_ok": obj.null_ok,
        }
    if isinstance(obj, psycopg.pq.PGresult) or isinstance(obj, psycopg_binary.pq.PGresult):
        return {
            "status": obj.status,
            "num_tuples": obj.num_tuples,
            "num_fields": obj.num_fields,
            "fields": obj.fields,
        }
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


# The observer captures all requests and responses from the database
class Observer:
    def __getattr__(self, attr):
        if attr not in self.__dict__:
            if self.target:
                return getattr(self.target, attr)
            return None
        return super().__getattr__(attr)


class PoolObserver(Observer):
    mode = SnapshotMode.RECORD

    def __init__(self, pool_manager: LRUConnectionPoolManager, *args, **kwargs):
        self.snapshot = []
        self.target = pool_manager

    @contextlib.contextmanager
    def get_connection(self, dbname: str, persistent: bool = False):
        if self.mode == SnapshotMode.RECORD:
            with self.target.get_connection(dbname, persistent) as conn:
                yield ConnectionObserver(conn, self.snapshot, self.mode)
        if self.mode == SnapshotMode.REPLAY:
            yield ConnectionObserver(None, self.snapshot, self.mode)
        # raise ValueError(f"Mode {self.mode} is not supported")



class ConnectionObserver(Observer):
    def __init__(self, conn: Connection, snapshot: list, mode: str):
        # print(f"Initializing connection observer")
        self.snapshot = snapshot
        self.target = conn
        self.mode = mode

    def __enter__(self):
        if self.target:
            self.target = self.target.__enter__()
        return self

    def __exit__(
        self,
        exc_type,
        exc_val,
        exc_tb,
    ):
        if self.target:
            return self.target.__exit__(exc_type, exc_val, exc_tb)
        return None

    @contextlib.contextmanager
    def cursor(self, *args, **kwargs):
        # print(f"Getting cursor")
        if self.mode == SnapshotMode.RECORD:
            with self.target.cursor(*args, **kwargs) as cursor:
                yield CursorObserver(cursor, self.snapshot, self.mode)
        if self.mode == SnapshotMode.REPLAY:
            yield CursorObserver(None, self.snapshot, self.mode)
        # raise ValueError(f"Mode {self.mode} is not supported")

    @property
    def info(self):
        if self.target:
            return self.target.info

        # Replay connection is always OK
        class Info:
            status = psycopg.pq.ConnStatus.OK
            dbname = ""

        return Info()


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

    @property
    def description(self):
        if self.target:
            description = self.target.description
            self.snapshot.append(description)
            return description
        columns = [[c['name']] for c in self.replay()]
        return columns

    @property
    def pgresult(self):
        if self.target:
            result = self.target.pgresult
            self.snapshot.append(result)
            return result
        result = self.replay()[0]
        print("result", result)
        pgresult = psycopg.pq.PGresult()
        pgresult.status = result.get('status')
        return result

def inject_snapshot_observer(check: PostgreSql, snapshot_mode: SnapshotMode):
    observer = PoolObserver(check.db_pool)
    observer.mode = snapshot_mode
    observer.snapshot = []

    if snapshot_mode == SnapshotMode.REPLAY:
        observer.snapshot = read_file(snapshot_file_path(SnapshotFileType.REQUESTS))
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


def validate_snapshot(aggregator: AggregatorStub, check: PostgreSql):
    observer = check.db_pool
    output = serialize_aggregator(aggregator)

    if observer.mode == SnapshotMode.RECORD:
        write_file(observer.snapshot, snapshot_file_path(SnapshotFileType.REQUESTS))
        write_file(output, snapshot_file_path(SnapshotFileType.EXPECTED))
    elif observer.mode == SnapshotMode.REPLAY:
        with open(snapshot_file_path(SnapshotFileType.EXPECTED), "r") as f:
            expected = orjson.loads(f.read())
        write_file(output, snapshot_file_path(SnapshotFileType.OUTPUT))
        assert output == expected
