# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
import inspect
import threading
from typing import Callable, Dict

import psycopg2


class ConnectionInfo:
    def __init__(
        self,
        connection: psycopg2.extensions.connection,
        deadline: int,
        active: bool,
        last_accessed: int,
        thread: threading.Thread,
    ):
        self.connection = connection
        self.deadline = deadline
        self.active = active
        self.last_accessed = last_accessed
        self.thread = thread


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
    Connection eviction should be handled by the calling code. Call done() on a connection
    when it is no longer necessary, so it will be marked evictable.
    If the connection pool is full, try to evict a connection with evict_lru() until a
    connection is evicted, then try get_connection() again.
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

    def get_connection(self, dbname: str, ttl_ms: int):
        """
        Grab a connection from the pool if the database is already connected.
        If max_conns is specified, and the database isn't already connected,
        make a new connection IFF the max_conn limit hasn't been reached.
        If we can't fit the connection into the pool, return None.
        """
        self.prune_connections()
        with self._mu:
            conn = self._conns.pop(dbname, ConnectionInfo(None, None, None, None, None))
            db = conn.connection
            if db is None or db.closed:
                if self.max_conns is not None and len(self._conns) == self.max_conns:
                    return None
                self._stats.connection_opened += 1
                db = self.connect_fn(dbname)

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
            )
            return db

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

    def done(self, dbname: str) -> None:
        """
        Mark a connection as done being used, so it can be evicted from the pool.
        This function does not evict connections from the pool; it just marks them
        as inactive.
        done() can only be called on a connection in the same thread that the connection
        was made.
        """
        with self._mu:
            if self._conns[dbname].thread != threading.current_thread():
                raise RuntimeError(
                    "Cannot call done() for this dbname on this thread. Done() can only be called \
                                   from the same thread the connection was made."
                )

            self._conns[dbname].active = False

    def evict_lru(self) -> str:
        """
        Evict and close the inactive connection which was least recently used.
        Return the dbname connection that was evicted.
        """
        with self._mu:
            conns_list = dict(self._conns)
            while True:
                if not conns_list:
                    break

                eviction_candidate = self._get_lru(conns_list)
                if self._conns[eviction_candidate].active:
                    del conns_list[eviction_candidate]
                    continue

                # eviction candidate successfully found
                self._terminate_connection_unsafe(eviction_candidate)
                return eviction_candidate

            # Could not evict a candidate; return None, calling code should keep trying.
            return None

    def _get_lru(self, connections: Dict[str, ConnectionInfo]) -> str:
        return min(connections, key=lambda t: self._conns[t].last_accessed)

    def _terminate_connection_unsafe(self, dbname: str):
        db = self._conns.pop(dbname, ConnectionInfo(None, None, None, None, None)).connection
        if db is not None:
            try:
                self._stats.connection_closed += 1
                db.close()
            except Exception:
                self._stats.connection_closed_failed += 1
                self._log.exception("failed to close DB connection for db=%s", dbname)
                return False
        return True
