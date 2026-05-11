# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Callable, List, Optional  # noqa: F401
from urllib.parse import urlparse

from datadog_checks.base import ConfigurationError, is_affirmative

from . import queries
from .types import Instance  # noqa: F401

DEFAULT_STATISTICS_COMPONENTS = [
    'COMMANDLOG',
    'CPU',
    'GC',
    'INDEX',
    'IOSTATS',
    'LATENCY',
    'MEMORY',
    'PROCEDURE',
    'SNAPSHOTSTATUS',
    'TABLE',
]

STATISTICS_COMPONENTS_MAP = {
    'COMMANDLOG': queries.CommandLogMetrics,
    'CPU': queries.CPUMetrics,
    'EXPORT': queries.ExportMetrics,
    'GC': queries.GCMetrics,
    'IDLETIME': queries.IdleTimeMetrics,
    'IMPORT': queries.ImportMetrics,
    'INDEX': queries.IndexMetrics,
    'IOSTATS': queries.IOStatsMetrics,
    'LATENCY': queries.LatencyMetrics,
    'MEMORY': queries.MemoryMetrics,
    'PROCEDURE': queries.ProcedureMetrics,
    'PROCEDUREOUTPUT': queries.ProcedureOutputMetrics,
    'PROCEDUREPROFILE': queries.ProcedureProfileMetrics,
    'QUEUE': queries.QueueMetrics,
    'SNAPSHOTSTATUS': queries.SnapshotStatusMetrics,
    'TABLE': queries.TableMetrics,
}

DEFAULT_PORT = 21212


def _strip_sources(query_def):
    """Split the `source` annotations out of a query definition.

    Returns a tuple of:
      - a copy of the query definition suitable for QueryManager (no `source` keys), and
      - a list of VoltDB source column names, one per column entry.
    """
    columns = query_def['columns']
    cleaned_columns = []
    sources = []
    for column in columns:
        if isinstance(column, dict) and 'source' in column:
            source = column['source']
            sources.append(source)
            cleaned_columns.append({k: v for k, v in column.items() if k != 'source'})
        else:
            sources.append(None)
            cleaned_columns.append(column)
    cleaned = dict(query_def)
    cleaned['columns'] = cleaned_columns
    return cleaned, sources


MODE_NATIVE = 'native'
MODE_HTTP = 'http'


class Config(object):
    def __init__(self, instance, debug=lambda *args: None, warning=lambda *args: None):
        # type: (Instance, Callable, Callable) -> None
        self._debug = debug

        host = instance.get('host')  # type: Optional[str]
        port = instance.get('port')  # type: Optional[int]
        url = instance.get('url')  # type: Optional[str]
        username = instance.get('username', '')  # type: str
        password = instance.get('password', '')  # type: str
        password_hashed = is_affirmative(instance.get('password_hashed', False))  # type: bool
        use_ssl = instance.get('use_ssl')
        ssl_config_file = instance.get('ssl_config_file')  # type: Optional[str]
        connect_timeout = instance.get('connect_timeout', 8)  # type: float
        # `procedure_timeout` of 0 (or negative) disables the timeout, matching
        # the `voltdbclient` semantics where `None` means wait forever.
        procedure_timeout = instance.get('procedure_timeout', 60)  # type: Optional[float]
        if procedure_timeout is not None and procedure_timeout <= 0:
            procedure_timeout = None
        statistics_components = instance.get('statistics_components', DEFAULT_STATISTICS_COMPONENTS)
        tags = instance.get('tags', [])  # type: List[str]

        # Mode selection: presence of `url` activates the HTTP transport (talks
        # to the VoltDB Management Center HTTP/JSON endpoint), otherwise we use
        # the native binary client against `host`/`port`. The two transports
        # share the rest of the configuration (auth, statistics components,
        # custom queries, tags).
        if url:
            mode = MODE_HTTP
            parsed = urlparse(url)
            url_host = parsed.hostname
            if not url_host:  # pragma: no cover
                raise ConfigurationError("URL must contain a host")
            url_port = parsed.port
            if not url_port:
                url_port = 443 if parsed.scheme == 'https' else 80
                self._debug('No port detected in url, defaulting to port %d', url_port)
            if not username or not password:
                raise ConfigurationError("'username' and 'password' are required when 'url' is set")
            netloc = (url_host, url_port)
        else:
            mode = MODE_NATIVE
            if port is None:
                port = DEFAULT_PORT
            use_ssl = is_affirmative(use_ssl) if use_ssl is not None else False
            if not host:
                raise ConfigurationError("'host' is required (or set 'url' to use the HTTP/VMC transport)")
            if not isinstance(port, int) or port <= 0:
                raise ConfigurationError('port must be a positive integer')
            netloc = (host, port)

        if not isinstance(statistics_components, list):
            raise ConfigurationError("'statistics_components' must be a list of strings")

        self.queries = []
        # Map from query string to the ordered list of VoltDB column names that
        # back each output column. Used at runtime to look up values by name.
        self.query_sources = {}  # type: dict
        for elem in statistics_components:
            if not isinstance(elem, str):
                raise ConfigurationError(
                    "'statistics_components' must be a list of strings. Element {} is not a string.".format(elem)
                )
            if elem not in STATISTICS_COMPONENTS_MAP:
                raise ConfigurationError(
                    "Statistic component '{}' is not supported. Must be one of [{}].".format(
                        elem, ', '.join(STATISTICS_COMPONENTS_MAP.keys())
                    )
                )
            query_def, sources = _strip_sources(STATISTICS_COMPONENTS_MAP[elem])
            self.queries.append(query_def)
            if sources:
                self.query_sources[query_def['query']] = sources

        self.mode = mode
        self.url = url
        self.host = host
        self.port = port
        self.netloc = netloc
        self.username = username
        self.password = password
        self.password_hashed = password_hashed
        self.use_ssl = use_ssl
        self.ssl_config_file = ssl_config_file
        self.connect_timeout = connect_timeout
        self.procedure_timeout = procedure_timeout
        self.tags = tags
