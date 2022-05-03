import re

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    default_json_event_encoding,
    obfuscate_sql_with_metadata,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


ALWAYSON_QUERY = re.sub(
    r"\s+",
    " ",
    """\
""",
).strip()


class SqlserverAlwaysOn(DBMAsyncJob):

    DEFAULT_COLLECTION_INTERVAL = 10
    MAX_PAYLOAD_BYTES = 19e6

    def __init__(self, check):
        self.check = check
        self.log = check.log
        collection_interval = float(
            check.alwayson_config.get(
                "collection_interval", SqlserverAlwaysOn.DEFAULT_COLLECTION_INTERVAL
            )
        )
        if collection_interval <= 0:
            collection_interval = SqlserverAlwaysOn.DEFAULT_COLLECTION_INTERVAL
        self.collection_interval = collection_interval
        super(SqlserverAlwaysOn, self).__init__(
            check,
            run_sync=is_affirmative(check.alwayson_config.get("run_sync", False)),
            enabled=is_affirmative(check.alwayson_config.get("enabled", True)),
            expected_db_exceptions=(),
            min_collection_interval=check.min_collection_interval,
            dbms="sqlserver",
            rate_limit=1 / float(collection_interval),
            job_name="query-alwayson",
            shutdown_callback=self._close_db_conn,
        )
        self._conn_key_prefix = "dbm-alwayson-"
        self._alwayson_payload_max_bytes = SqlserverAlwaysOn.MAX_PAYLOAD_BYTES
        self._exec_requests_cols_cached = None

    def _close_db_conn(self):
        pass

    def run_job(self):
        self._collect_alwayson()

    def _collect_alwayson(self):
        pass
