# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager
from typing import Any, Dict, Iterator

import rethinkdb
import six

from datadog_checks.base import AgentCheck

try:
    rethinkdb.r
except AttributeError:
    if not six.PY2:
        # This would be unexpected.
        raise

    # HACK: running `import rethinkdb` on Python 2.7 made it import our `rethinkdb` package,
    # instead of the RethinkDB Python client package. Let's hack our way around this.
    # NOTE: we deal with this edge case in an 'except' block (instead of proactively checking for `six.PY2`) so that
    # IDEs and linters don't get confused.
    import importlib

    rethinkdb = importlib.import_module('rethinkdb')  # type: ignore


class RethinkDBCheck(AgentCheck):
    def check(self, instance):
        # type: (Dict[str, Any]) -> None
        with _connect(database='rethinkdb', host='localhost', port=28015) as conn:
            server = conn.server()  # type: Dict[str, Any]
            tags = ['server:{}'.format(server['name'])]
            self.service_check('rethinkdb.can_connect', self.OK, tags=tags)


@contextmanager
def _connect(database, host, port):
    # type: (str, str, int) -> Iterator[rethinkdb.net.Connection]
    with rethinkdb.r.connect(db=database, host=host, port=port) as conn:
        yield conn
