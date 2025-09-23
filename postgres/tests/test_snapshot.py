# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import contextlib

import orjson
import psycopg
import pytest
from psycopg import Connection, Cursor

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.postgres.connection_pool import LRUConnectionPoolManager

from .conftest import SnapshotMode
from .snapshots import SnapshotFileType, read_file, serialize_aggregator, snapshot_file_path, write_file


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
        if self.mode == SnapshotMode.RECORD:
            yield CursorObserver(self.target.cursor(*args, **kwargs), self.snapshot, self.mode)
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
    check.run()

    # Sanity check that the check ran
    aggregator.assert_metric("postgresql.running", count=1)

    output = serialize_aggregator(aggregator)

    if observer.mode == SnapshotMode.RECORD:
        write_file(observer.snapshot, snapshot_file_path(SnapshotFileType.REQUESTS))
        write_file(output, snapshot_file_path(SnapshotFileType.EXPECTED))
    elif observer.mode == SnapshotMode.REPLAY:
        with open(snapshot_file_path(SnapshotFileType.EXPECTED), "r") as f:
            expected = orjson.loads(f.read())
        write_file(output, snapshot_file_path(SnapshotFileType.OUTPUT))
        assert output == expected
