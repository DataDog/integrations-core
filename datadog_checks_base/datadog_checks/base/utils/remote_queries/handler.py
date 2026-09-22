# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""The composed capability contract behind AgentCheck.run_remote_query."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any, Protocol

from datadog_checks.base.utils.remote_queries.contract import RemoteQueryEvent
from datadog_checks.base.utils.remote_queries.timing import RemoteQueryProducerTimings

# The closed operation vocabulary the bridge routes: resolving a target without executing
# customer SQL, and executing one query into JSON result pages.
REMOTE_QUERY_OPERATION_RESOLVE_TARGET = 'resolve_target'
REMOTE_QUERY_OPERATION_PRODUCE_JSON_PAGES = 'produce_json_pages'
REMOTE_QUERY_OPERATIONS = frozenset((REMOTE_QUERY_OPERATION_RESOLVE_TARGET, REMOTE_QUERY_OPERATION_PRODUCE_JSON_PAGES))


class RemoteQueryHandler(Protocol):
    """The remote-query capability of one loaded check, composed with it.

    `AgentCheck.get_remote_query_handler` returns one handler per bridge call, and its
    presence is the sole capability gate: a handler implements the complete closed Remote
    Query protocol — resolve and execute — while None means the check has no Remote Query
    capability at all. Handlers are cheap to construct and hold the check they serve, never
    check-global or process-global request state: every request owns its call. Requests are
    decoded JSON objects; each method validates its operation's schema before accessing
    database state, and only metadata events cross the Agent's emit callback, never rows.
    """

    def resolve(self, request: Mapping[str, Any]) -> Iterator[RemoteQueryEvent]:
        """Yield the per-check target verdict without executing customer SQL or uploading data."""
        ...

    def execute(self, request: Mapping[str, Any], timings: RemoteQueryProducerTimings) -> Iterator[RemoteQueryEvent]:
        """Yield STARTED then a final receipt or error; upload result bytes outside the bridge."""
        ...
