# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Callable, List, Optional  # noqa: F401

from six.moves.urllib.parse import urlparse

from datadog_checks.base import ConfigurationError, is_affirmative

from . import queries
from .types import Instance  # noqa: F401

DEFAULT_STATISTICS_COMPONENTS = [
    "COMMANDLOG",
    "CPU",
    "GC",
    "INDEX",
    "IOSTATS",
    "LATENCY",
    "MEMORY",
    "PROCEDURE",
    "SNAPSHOTSTATUS",
    "TABLE",
]

STATISTICS_COMPONENTS_MAP = {
    "COMMANDLOG": queries.CommandLogMetrics,
    "CPU": queries.CPUMetrics,
    "EXPORT": queries.ExportMetrics,
    "GC": queries.GCMetrics,
    "IDLETIME": queries.IdleTimeMetrics,
    "IMPORT": queries.ImportMetrics,
    "INDEX": queries.IndexMetrics,
    "IOSTATS": queries.IOStatsMetrics,
    "LATENCY": queries.LatencyMetrics,
    "MEMORY": queries.MemoryMetrics,
    "PROCEDURE": queries.ProcedureMetrics,
    "PROCEDUREOUTPUT": queries.ProcedureOutputMetrics,
    "PROCEDUREPROFILE": queries.ProcedureProfileMetrics,
    "QUEUE": queries.QueueMetrics,
    "SNAPSHOTSTATUS": queries.SnapshotStatusMetrics,
    "TABLE": queries.TableMetrics,
}


class Config(object):
    def __init__(self, instance, debug=lambda *args: None):
        # type: (Instance, Callable) -> None
        self._debug = debug

        url = instance.get('url')  # type: Optional[str]
        username = instance.get('username')  # type: Optional[str]
        password = instance.get('password')  # type: Optional[str]
        statistics_components = instance.get('statistics_components', DEFAULT_STATISTICS_COMPONENTS)
        password_hashed = is_affirmative(instance.get('password_hashed', False))  # type: bool
        tags = instance.get('tags', [])  # type: List[str]

        if not url:
            raise ConfigurationError('url is required')

        if not username or not password:
            raise ConfigurationError('username and password are required')

        parsed_url = urlparse(url)

        host = parsed_url.hostname
        if not host:  # pragma: no cover  # Mostly just type safety.
            raise ConfigurationError('URL must contain a host')

        port = parsed_url.port
        if not port:
            port = 443 if parsed_url.scheme == 'https' else 80
            self._debug('No port detected, defaulting to port %d', port)

        if not isinstance(statistics_components, list):
            raise ConfigurationError("'statistics_components' must be a list of strings")

        self.queries = []
        for elem in statistics_components:
            if not isinstance(elem, str):
                raise ConfigurationError(
                    "'statistics_components' must be a list of strings. Element {} is not a string.".format(elem)
                )
            if elem not in STATISTICS_COMPONENTS_MAP:
                raise ConfigurationError(
                    "Statistic component '{}' is not supported. Must be one of [{}].".format(
                        elem, ", ".join(STATISTICS_COMPONENTS_MAP.keys())
                    )
                )
            self.queries.append(STATISTICS_COMPONENTS_MAP[elem])

        self.url = url
        self.netloc = (host, port)
        self.username = username
        self.password = password
        self.password_hashed = password_hashed
        self.tags = tags
