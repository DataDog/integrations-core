# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from operator import attrgetter
from time import time
from typing import TYPE_CHECKING

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

from .activity import normalize_activity, read_activity
from .connection import Db2Connection, Db2ConnectionError

if TYPE_CHECKING:
    from .config_models import InstanceConfig
    from .ibm_db2 import IbmDb2Check

# Matches METRICS_PAYLOAD_MAX_BYTES in query_metrics.py.
ACTIVITY_PAYLOAD_MAX_BYTES = 20_000_000


def _json_size(value: dict) -> int:
    encoded = json.dumps(value, default=default_json_event_encoding)
    return len(encoded.encode('utf-8') if isinstance(encoded, str) else encoded)


class QuerySamplesCollector(DBMAsyncJob):
    def __init__(self, check: IbmDb2Check, config: InstanceConfig):
        super().__init__(
            check,
            config_host=config.host,
            min_collection_interval=config.min_collection_interval,
            enabled=config.query_activity.enabled,
            rate_limit=1 / config.query_activity.collection_interval,
            expected_db_exceptions=(Db2ConnectionError,),
            dbms=check.dbms,
            job_name='query-activity',
            features=['query_activity'],
        )
        self._config = config
        self._connection = Db2Connection(check, config)

    @tracked_method(agent_check_getter=attrgetter('_check'))
    def run_job(self) -> None:
        try:
            connection = self._connection.ensure_connected()
        except Db2ConnectionError as error:
            self._check.health.submit_exception_health_event(error, data={'job_name': 'query-activity'})
            raise
        rows, stats = read_activity(connection)
        observations = []
        payload = {
            'ddsource': 'ibm_db2',
            'dbm_type': 'activity',
            'host': self._check.reported_hostname,
            'database_instance': self._check.database_identifier,
            'ddagentversion': self._check.agent_version,
            'ibm_db2_version': self._check.dbms_version,
            'timestamp': time() * 1000,
            'collection_interval': self._config.query_activity.collection_interval,
            'ddtags': self._check.tag_manager.get_tags(include_internal=False),
            'service': self._config.service,
            'ibm_db2_activity': observations,
        }
        size = _json_size(payload)
        stats.update(normalization_dropped=0, payload_limit=0)
        for row in rows:
            normalized = normalize_activity(row, self._config.db)
            if normalized is None:
                stats['normalization_dropped'] += 1
                continue
            next_size = size + _json_size(normalized) + (2 if observations else 0)
            if next_size > ACTIVITY_PAYLOAD_MAX_BYTES:
                stats['payload_limit'] = 1
                break
            size = next_size
            observations.append(normalized)
        for name, value in stats.items():
            self._check.gauge(f'dd.ibm_db2.query_activity.{name}', value, **self._check.debug_stats_kwargs())
        self._check.database_monitoring_query_activity(json.dumps(payload, default=default_json_event_encoding))

    def shutdown(self) -> None:
        self._connection.close()
