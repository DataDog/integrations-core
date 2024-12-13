# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.config import is_affirmative

from .base import SqlserverDatabaseMetricsBase

XE_RING_BUFFER = "ring_buffer"
XE_EVENT_FILE = "event_file"

XE_SESSION_STATUS_QUERY = {
    "name": "sys.dm_xe_sessions",
    "query": """SELECT
s.name as session_name,
CASE
    WHEN r.event_session_id IS NULL THEN 0
    ELSE 1
END AS session_status
FROM sys.dm_xe_sessions as s
LEFT OUTER JOIN sys.server_event_sessions r
    ON s.name = r.name""",
    "columns": [
        {"name": "session_name", "type": "tag"},
        {"name": "xe.session_status", "type": "gauge"},
    ],
}

XE_EVENTS_NOT_IN_XML = {
    "name": "sys.dm_xe_session_targets",
    "query": """SELECT name session_name,
    target_data.value('(RingBufferTarget/@eventCount)[1]', 'int') -
    target_data.value('count(RingBufferTarget/event)', 'int') AS events_not_in_xml
    FROM
    ( SELECT s.name, CAST(target_data AS XML) AS target_data
        FROM sys.dm_xe_sessions as s
        INNER JOIN sys.dm_xe_session_targets AS st
           ON s.address = st.event_session_address
       WHERE st.target_name = N'ring_buffer' ) AS n""",
    "columns": [
        {"name": "session_name", "type": "tag"},
        {"name": "xe.events_not_in_xml", "type": "gauge"},
    ],
}


class SQLServerXESessionMetrics(SqlserverDatabaseMetricsBase):
    @property
    def enabled(self):
        self.deadlocks_config: dict = self.config.deadlocks_config
        return self.config.database_metrics_config["xe_metrics"]["enabled"] or is_affirmative(
            self.deadlocks_config.get('enabled', False)
        )

    @property
    def collection_interval(self) -> int:
        '''
        Returns the interval in seconds at which to collect XE sessopm metrics.
        '''
        return 60

    @property
    def queries(self):
        # make copies of the query to avoid modifying the originals
        # in case different instances have different collection intervals
        query_status = XE_SESSION_STATUS_QUERY.copy()
        query_status['collection_interval'] = self.collection_interval
        query_events_not_in_xml = XE_EVENTS_NOT_IN_XML.copy()
        query_events_not_in_xml['collection_interval'] = self.collection_interval
        return [query_status, query_events_not_in_xml]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"engine_edition={self.engine_edition}, "
            f"collection_interval={self.collection_interval})"
        )
