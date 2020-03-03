# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class RethinkDBError(Exception):
    """Base class for exceptions raised by the RethinkDB check."""


class CouldNotConnect(RethinkDBError):
    """Failed to connect to a RethinkDB server."""


class VersionCollectionFailed(RethinkDBError):
    """Failed to collect or parse the RethinkDB version from a server."""
