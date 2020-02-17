from contextlib import contextmanager
from typing import Any, Dict, Iterator

from rethinkdb import r
from rethinkdb.net import Connection


class MockConnectionInstance(object):
    def __init__(self, parent, *args, **kwargs):
        # type: (MockConnection, *Any, **Any) -> None
        self._parent = parent

    # Implement the connection instance interface used by RethinkDB.

    def client_address(self):
        # type: () -> str
        return 'testserver'

    def client_port(self):
        # type: () -> int
        return 28015

    def connect(self, timeout):
        # type: (float) -> MockConnection
        return self._parent

    def reconnect(self, timeout):
        # type: (float) -> MockConnection
        return self.connect(timeout)

    def is_open(self):
        # type: () -> bool
        return True

    def run_query(self, query, noreply):
        # type: (Any, bool) -> Iterator[Dict[str, Any]]
        return self._parent.mock_rows()


class MockConnection(Connection):
    """
    A RethinkDB connection type that mocks all queries by sending a deterministic set of rows.

    Inspired by:
    https://github.com/rethinkdb/rethinkdb-python/blob/9aa68feff16dc984406ae0e276f24e87df89b334/rethinkdb/asyncio_net/net_asyncio.py
    """

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        rows = kwargs.pop('rows')
        super(MockConnection, self).__init__(MockConnectionInstance, *args, **kwargs)
        self.rows = rows

    def mock_rows(self):
        # type: () -> Iterator[Dict[str, Any]]
        for row in self.rows:
            yield row


@contextmanager
def patch_connection_type(conn_type):
    # type: (type) -> Iterator[None]
    initial_conn_type = r.connection_type
    r.connection_type = conn_type
    try:
        yield
    finally:
        r.connection_type = initial_conn_type
