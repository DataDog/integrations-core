import datetime
import inspect
import threading
from collections import namedtuple

import psycopg2

ConnectionWithTTL = namedtuple("ConnectionWithTTL", "connection deadline")


class MultiDatabaseConnectionPool(object):
    """
    Manages a connection pool of connections across many logical databases with a maximum
    of 1 conn per database. Traditional connection pools manage a set of connections to a
    single database, however the usage patterns of the Agent application should aim to have
    minimal footprint and reuse a single connection as much as possible.

    Even when limited to a single connection per database, an instance with hundreds of
    databases still present a connection overhead risk. This class provides a mechanism
    to prune connections to a database which were not used in the time specified by their
    TTL.
    """

    def __init__(self, connect_fn, max_connections=-1):
        self._mu = threading.Lock()
        self._conns = dict()
        self._max_connections = max_connections

        connect_sig = inspect.signature(connect_fn)
        if len(connect_sig.parameters) != 1:
            raise ValueError(
                "Invalid signature for the connection function. "
                "A single parameter for dbname is expected, got signature: {}".format(connect_sig)
            )
        self.connect_fn = connect_fn

    def get_connection(self, dbname: str, ttl_ms: int):
        self.prune_connections()
        with self._mu:
            db, _ = self._conns.pop(dbname, ConnectionWithTTL(None, None))
            if db is None or db.closed:
                db = self.connect_fn(dbname)

            if db.status != psycopg2.extensions.STATUS_READY:
                # Some transaction went wrong and the connection is in an unhealthy state. Let's fix that
                db.rollback()

            deadline = datetime.datetime.now() + datetime.timedelta(milliseconds=ttl_ms)
            self._conns[dbname] = ConnectionWithTTL(db, deadline)
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
                    self._terminate_connection_unsafe(dbname)

        # TODO: Prune max connections
        # if self._max_connections > 0 and len(self._conns) > self._max_connections:
        #     sorted([(dbname, db) for dbname, db in self._conns.items()])

    def close_all_connections(self):
        success = True
        with self._mu:
            for dbname in list(self._conns.keys()):
                if not self._terminate_connection_unsafe(dbname):
                    success = False
        return success

    def _terminate_connection_unsafe(self, dbname: str):
        db, _ = self._conns.pop(dbname, ConnectionWithTTL(None, None))
        if db is not None:
            try:
                db.close()
            except Exception:
                self._log.exception("failed to close DB connection for db=%s", dbname)
                return False
        return True
