# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import contextlib
import datetime
import inspect
import threading
import time
from typing import Callable, Dict

import psycopg2


class ConnectionPoolFullError(Exception):
    def __init__(self, size, timeout):
        self.size = size
        self.timeout = timeout

    def __str__(self):
        return "Could not insert connection in pool size {} within {} seconds".format(self.size, self.timeout)


class ConnectionInfo:
    def __init__(
        self,
        connection: psycopg2.extensions.connection,
        deadline: int,
        active: bool,
        last_accessed: int,
        thread: threading.Thread,
        persistent: bool,
    ):
        self.connection = connection
        self.deadline = deadline
        self.active = active
        self.last_accessed = last_accessed
        self.thread = thread
        self.persistent = persistent


class MultiDatabaseConnectionPool(object):
    """
    Manages a connection pool across many logical databases with a maximum of 1 conn per
    database. Traditional connection pools manage a set of connections to a single database,
    however the usage patterns of the Agent application should aim to have minimal footprint
    and reuse a single connection as much as possible.

    Even when limited to a single connection per database, an instance with hundreds of
    databases still present a connection overhead risk. This class provides a mechanism
    to prune connections to a database which were not used in the time specified by their
    TTL.

    If max_conns is specified, the connection pool will limit concurrent connections.
    """

    class Stats(object):
        def __init__(self):
            self.connection_opened = 0
            self.connection_pruned = 0
            self.connection_closed = 0
            self.connection_closed_failed = 0

        def __repr__(self):
            return str(self.__dict__)

        def reset(self):
            self.__init__()

    def __init__(self, connect_fn: Callable[[str], None], max_conns: int = None):
        self.max_conns: int = max_conns
        self._stats = self.Stats()
        self._mu = threading.RLock()
        self._conns: Dict[str, ConnectionInfo] = {}

        if hasattr(inspect, 'signature'):
            connect_sig = inspect.signature(connect_fn)
            if len(connect_sig.parameters) != 1:
                raise ValueError(
                    "Invalid signature for the connection function. "
                    "A single parameter for dbname is expected, got signature: {}".format(connect_sig)
                )
        self.connect_fn = connect_fn

    def _get_connection_raw(
        self,
        dbname: str,
        ttl_ms: int,
        timeout: int = None,
        startup_fn: Callable[[psycopg2.extensions.connection], None] = None,
        persistent: bool = False,
    ) -> psycopg2.extensions.connection:
        """
        Return a connection from the pool.
        Pass a function to startup_func if there is an action needed with the connection
        when re-establishing it.
        """
        start = datetime.datetime.now()
        self.prune_connections()
        with self._mu:
            conn = self._conns.pop(dbname, None)
            db = conn.connection if conn else None
            if db is None or db.closed:
                if self.max_conns is not None:
                    # try to free space until we succeed
                    while len(self._conns) >= self.max_conns:
                        self.prune_connections()
                        self.evict_lru()
                        if timeout is not None and (datetime.datetime.now() - start).total_seconds() > timeout:
                            raise ConnectionPoolFullError(self.max_conns, timeout)
                        time.sleep(0.01)
                        continue
                self._stats.connection_opened += 1
                db = self.connect_fn(dbname)
                if startup_fn:
                    startup_fn(db)
            else:
                # if already in pool, retain persistence status
                persistent = conn.persistent

            if db.status != psycopg2.extensions.STATUS_READY:
                # Some transaction went wrong and the connection is in an unhealthy state. Let's fix that
                db.rollback()

            deadline = datetime.datetime.now() + datetime.timedelta(milliseconds=ttl_ms)
            self._conns[dbname] = ConnectionInfo(
                connection=db,
                deadline=deadline,
                active=True,
                last_accessed=datetime.datetime.now(),
                thread=threading.current_thread(),
                persistent=persistent,
            )
            return db

    @contextlib.contextmanager
    def get_connection(
        self,
        dbname: str,
        ttl_ms: int,
        timeout: int = None,
        startup_fn: Callable[[psycopg2.extensions.connection], None] = None,
        persistent: bool = False,
    ):
        """
        Grab a connection from the pool if the database is already connected.
        If max_conns is specified, and the database isn't already connected,
        make a new connection if the max_conn limit hasn't been reached.
        Blocks until a connection can be added to the pool,
        and optionally takes a timeout in seconds.
        Note that leaving a connection context here does NOT close the connection in psycopg2;
        connections must be manually closed by `close_all_connections()`.
        """
        try:
            with self._mu:
                db = self._get_connection_raw(dbname, ttl_ms, timeout, startup_fn, persistent)
            yield db
        finally:
            with self._mu:
                try:
                    self._conns[dbname].active = False
                except KeyError:
                    # if self._get_connection_raw hit an exception, self._conns[dbname] didn't get populated
                    pass

    def prune_connections(self):
        """
        This function should be called periodically to prune all connections which have not been
        accessed since their TTL. This means that connections which are actually active on the
        server can still be closed with this function. For instance, if a connection is opened with
        ttl 1000ms, but the query it's running takes 5000ms, this function will still try to close
        the connection mid-query.
        """
        with self._mu:
            now = datetime.datetime.now()
            for dbname, conn in list(self._conns.items()):
                if conn.deadline < now:
                    self._stats.connection_pruned += 1
                    self._terminate_connection_unsafe(dbname)

    def close_all_connections(self):
        success = True
        with self._mu:
            while self._conns:
                dbname = next(iter(self._conns))
                if not self._terminate_connection_unsafe(dbname):
                    success = False
        return success

    def evict_lru(self) -> str:
        """
        Evict and close the inactive connection which was least recently used.
        Return the dbname connection that was evicted or None if we couldn't evict a connection.
        """
        with self._mu:
            sorted_conns = sorted(self._conns.items(), key=lambda i: i[1].last_accessed)
            for name, conn_info in sorted_conns:
                if not conn_info.active and not conn_info.persistent:
                    self._terminate_connection_unsafe(name)
                    return name

            # Could not evict a candidate; return None
            return None

    def _terminate_connection_unsafe(self, dbname: str):
        db = self._conns.pop(dbname, ConnectionInfo(None, None, None, None, None, None)).connection
        if db is not None:
            try:
                self._stats.connection_closed += 1
                db.close()
            except Exception:
                self._stats.connection_closed_failed += 1
                return False
        return True
