# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Required for `import rethinkdb` to import the Python client instead of this package on Python 2.
from __future__ import absolute_import

from contextlib import contextmanager
from typing import Any, Dict, Iterator

import rethinkdb

from datadog_checks.base import AgentCheck


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
