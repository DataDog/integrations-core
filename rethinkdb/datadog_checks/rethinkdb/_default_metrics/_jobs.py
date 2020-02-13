# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import absolute_import

from typing import Iterator

import rethinkdb

from .._types import Metric


def collect_jobs(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect metrics about system jobs.

    See: https://rethinkdb.com/docs/system-jobs/
    """
    return iter(())  # TODO
