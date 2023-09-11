# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import contextlib
import datetime
import inspect
import threading
import time
from typing import Callable, Dict

from psycopg_pool import ConnectionPool

from datadog_checks.base import AgentCheck


class ConnectionPoolFullError(Exception):
    def __init__(self, size, timeout):
        self.size = size
        self.timeout = timeout

    def __str__(self):
        return "Could not insert connection in pool size {} within {} seconds".format(self.size, self.timeout)


class ConnectionInfo:
    def __init__(
        self,
        connection: ConnectionPool,
        deadline: int,
        active: bool,
        last_accessed: int,
        persistent: bool,
    ):
        self.connection = connection
        self.deadline = deadline
        self.active = active
        self.last_accessed = last_accessed
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

    def __init__(self, check: AgentCheck, connect_fn: Callable[[str, int, int], None], max_conns: int = None):
        self._check = check
        self._log = check.log
        self._config = check._config
        self.max_conns: int = max_conns
        self._stats = self.Stats()
        self._mu = threading.RLock()
        self._conns: Dict[str, ConnectionInfo] = {}

        if hasattr(inspect, 'signature'):
            connect_sig = inspect.signature(connect_fn)
            if not (len(connect_sig.parameters) >= 1):
                raise ValueError(
                    "Invalid signature for the connection function. "
                    "Expected parameters: dbname, min_pool_size, max_pool_size. "
                    "Got signature: {}".format(connect_sig)
                )
        self.connect_fn = connect_fn

    def _get_connection_pool(
        self,
        dbname: str,
        ttl_ms: int,
        timeout: int = None,
        min_pool_size: int = 1,
        max_pool_size: int = None,
        startup_fn: Callable[[ConnectionPool], None] = None,
        persistent: bool = False,
    ) -> ConnectionPool:
        """
        Return a connection pool for the requested database from the managed pool.
        Pass a function to startup_func if there is an action needed with the connection
        when re-establishing it.
        """
        start = datetime.datetime.now()
        self.prune_connections()
        with self._mu:
            conn = self._conns.pop(dbname, ConnectionInfo(None, None, None, None, None))
            db_pool = conn.connection
            if db_pool is None or db_pool.closed:
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
                db_pool = self.connect_fn(dbname, min_pool_size, max_pool_size)
                if startup_fn:
                    startup_fn(db_pool)
            else:
                # if already in pool, retain persistence status
                persistent = conn.persistent

            deadline = datetime.datetime.now() + datetime.timedelta(milliseconds=ttl_ms)
            self._conns[dbname] = ConnectionInfo(
                connection=db_pool,
                deadline=deadline,
                active=True,
                last_accessed=datetime.datetime.now(),
                persistent=persistent,
            )
            return db_pool

    @contextlib.contextmanager
    def get_connection(self, dbname: str, ttl_ms: int, timeout: int = None, persistent: bool = False):
        """
        Grab a connection from the pool if the database is already connected.
        If max_conns is specified, and the database isn't already connected,
        make a new connection if the max_conn limit hasn't been reached.
        Blocks until a connection can be added to the pool,
        and optionally takes a timeout in seconds.
        """
        with self._mu:
            pool = self._get_connection_pool(dbname=dbname, ttl_ms=ttl_ms, timeout=timeout, persistent=persistent)
            db = pool.getconn()
        try:
            yield db
        finally:
            with self._mu:
                try:
                    pool.putconn(db)
                    if not self._conns[dbname].persistent:
                        self._conns[dbname].active = False
                except KeyError:
                    # if self._get_connection_raw hit an exception, self._conns[conn_name] didn't get populated
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
            for conn_name, conn in list(self._conns.items()):
                if conn.deadline < now and not conn.active and not conn.persistent:
                    self._stats.connection_pruned += 1
                    self._terminate_connection_unsafe(conn_name)

    def close_all_connections(self, timeout=None):
        """
        Will block until all connections are terminated, unless the pre-configured timeout is hit
        :param timeout:
        :return:
        """
        success = True
        with self._mu:
            for dbname in list(self._conns):
                if not self._terminate_connection_unsafe(dbname, timeout):
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

    def _terminate_connection_unsafe(self, dbname: str, timeout: float = None) -> bool:
        if dbname not in self._conns:
            return True

        db = self._conns.pop(dbname).connection
        try:
            # pyscopg3 will IMMEDIATELY close the connection when calling close().
            # if timeout is not specified, psycopg will wait for the default 5s to stop the thread in the pool
            # if timeout is 0 or negative, psycopg will not wait for worker threads to terminate
            db.close() if timeout is None else db.close(timeout=timeout)
            self._stats.connection_closed += 1
        except Exception:
            self._stats.connection_closed_failed += 1
            self._log.exception("failed to close DB connection for db=%s", dbname)
            return False

        return True

    def get_main_db_pool(self, max_pool_conn_size: int = 3):
        """
        Returns a memoized, persistent psycopg connection pool to `self.dbname`.
        Is meant to be shared across multiple threads, and opens a preconfigured max number of connections.
        :return: a psycopg connection
        """
        conn = self._get_connection_pool(
            dbname=self._config.dbname,
            ttl_ms=self._config.idle_connection_timeout,
            max_pool_size=max_pool_conn_size,
            persistent=True,
        )
        return conn
