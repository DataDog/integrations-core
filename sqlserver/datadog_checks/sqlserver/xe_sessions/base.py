# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from time import time
import xml.etree.ElementTree as ET

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION
from datadog_checks.sqlserver.utils import is_azure_sql_database

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


def agent_check_getter(self):
    return self._check


class XESessionBase(DBMAsyncJob):
    """Base class for all XE session handlers"""
    
    def __init__(self, check, config, session_name):
        self.session_name = session_name
        self.tags = [t for t in check.tags if not t.startswith('dd.internal')]
        self._check = check
        self._log = check.log
        self._config = config
        self.collection_interval = 60  # Default for POC
        self.max_events = 100  # Default max events to collect
        
        super(XESessionBase, self).__init__(
            check,
            run_sync=True,
            enabled=True,  # Enabled for POC
            min_collection_interval=self._config.min_collection_interval,
            dbms="sqlserver",
            rate_limit=1 / float(self.collection_interval),
            job_name=f"xe_{session_name}",
            shutdown_callback=self._close_db_conn,
        )
        self._conn_key_prefix = f"dbm-xe-{session_name}-"
        self._is_azure_sql_database = False
        self._check_azure_status()
    
    def _check_azure_status(self):
        """Check if this is Azure SQL Database"""
        engine_edition = self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, "")
        self._is_azure_sql_database = is_azure_sql_database(engine_edition)
    
    def _close_db_conn(self):
        """Close database connection on shutdown"""
        pass
    
    def session_exists(self):
        """Check if this XE session exists and is running"""
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                # For Azure SQL Database support
                level = ""
                if self._is_azure_sql_database:
                    level = "database_"
                
                cursor.execute(
                    f"SELECT 1 FROM sys.dm_xe_{level}sessions WHERE name = %s", 
                    (self.session_name,)
                )
                return cursor.fetchone() is not None
    
    def _query_ring_buffer(self):
        """Query the ring buffer for this XE session"""
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                # For Azure SQL Database support
                level = ""
                if self._is_azure_sql_database:
                    level = "database_"
                    
                cursor.execute(f"""
                    SELECT CAST(t.target_data as xml) as event_data
                    FROM sys.dm_xe_{level}sessions s
                    JOIN sys.dm_xe_{level}session_targets t
                        ON s.address = t.event_session_address
                    WHERE s.name = %s
                    AND t.target_name = 'ring_buffer'
                """, (self.session_name,))
                
                result = cursor.fetchone()
                if not result:
                    return None
                
                return result[0]
    
    def _process_events(self, xml_data):
        """Process the events from the XML data - override in subclasses"""
        raise NotImplementedError
    
    def _create_event_payload(self, events):
        """Create a payload to send to Datadog"""
        if not events:
            return None
            
        return {
            "host": self._check.hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "sqlserver",
            "dbm_type": f"xe_{self.session_name}",
            "collection_interval": self.collection_interval,
            "ddtags": self.tags,
            "timestamp": time() * 1000,
            "sqlserver_version": self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            "sqlserver_engine_edition": self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            "cloud_metadata": self._config.cloud_metadata,
            "service": self._config.service,
            f"sqlserver_{self.session_name}_events": events,
        }
    
    def run_job(self):
        """Run the XE session collection job"""
        if not self.session_exists():
            self._log.warning(f"XE session {self.session_name} not found or not running")
            return
            
        xml_data = self._query_ring_buffer()
        if not xml_data:
            self._log.debug(f"No data found in ring buffer for session {self.session_name}")
            return
            
        events = self._process_events(xml_data)
        payload = self._create_event_payload(events)
        
        if payload:
            serialized_payload = json.dumps(payload, default=default_json_event_encoding)
            self._log.debug(f"Sending XE session payload: {serialized_payload[:200]}...")
            self._check.database_monitoring_query_activity(serialized_payload) 