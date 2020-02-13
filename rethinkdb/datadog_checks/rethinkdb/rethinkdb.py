# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Required for `import rethinkdb` to correctly import the client package (instead of this package) on Python 2.
from __future__ import absolute_import

from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator

import rethinkdb

from datadog_checks.base import AgentCheck

from ._default_metrics import collect_default_metrics
from ._types import Metric


class RethinkDBCheck(AgentCheck):
    """
    Collect metrics from a RethinkDB cluster.

    A set of default metrics is collected from system tables.
    """

    def check(self, instance):
        # type: (Dict[str, Any]) -> None
        with self.__submit_service_check():
            with rethinkdb.r.connect(db='rethinkdb', host='localhost', port=28015) as conn:
                for metric in collect_default_metrics(conn):
                    self.__submit_metric(metric)

    # NOTE: usage of private methods (double underscores) prevents name clashes with the base class.

    @contextmanager
    def __submit_service_check(self):
        # type: () -> Iterator[None]
        try:
            yield
        except rethinkdb.errors.ReqlDriverError:
            self.service_check('rethinkdb.can_connect', self.CRITICAL)
            raise
        else:
            self.service_check('rethinkdb.can_connect', self.OK)

    def __submit_metric(self, metric):
        # type: (Metric) -> None
        submit = getattr(self, metric['type'])  # type: Callable
        submit(metric['name'], value=metric['value'], tags=metric['tags'])

    # TODO: version metadata.
    # TODO: custom queries. (Hint: look at `QueryManager`.)
    # TODO: allow not sending default metrics.
    # TODO: decide if and how to deal with `identifier_format`: https://rethinkdb.com/api/python/table/#description
