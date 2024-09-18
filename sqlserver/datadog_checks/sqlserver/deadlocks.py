# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import xml.etree.ElementTree as ET
from datetime import datetime
from time import time

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.config import SQLServerConfig
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION
from datadog_checks.sqlserver.queries import DETECT_DEADLOCK_QUERY

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

MAX_DEADLOCKS = 100
MAX_PAYLOAD_BYTES = 19e6
DEFAULT_COLLECTION_INTERVAL = 600


def agent_check_getter(self):
    return self._check


class Deadlocks(DBMAsyncJob):
    def __init__(self, check, config: SQLServerConfig):
        self.tags = [t for t in check.tags if not t.startswith('dd.internal')]
        self._check = check
        self._log = self._check.log
        self._config = config
        self._last_deadlock_timestamp = time()
        self._max_deadlocks = config.deadlocks_config.get("max_deadlocks", MAX_DEADLOCKS)
        self._deadlock_payload_max_bytes = MAX_PAYLOAD_BYTES
        self.collection_interval = config.deadlocks_config.get("collection_interval", DEFAULT_COLLECTION_INTERVAL)
        super(Deadlocks, self).__init__(
            check,
            run_sync=True,
            enabled=self._config.deadlocks_config.get('enabled', True),
            expected_db_exceptions=(),
            min_collection_interval=self._config.min_collection_interval,
            dbms="sqlserver",
            rate_limit=1 / float(self.collection_interval),
            job_name="deadlocks",
            shutdown_callback=self._close_db_conn,
        )
        self._conn_key_prefix = "dbm-deadlocks-"
    
    def _close_db_conn(self):
        pass


    def obfuscate_no_except_wrapper(self, sql_text):
        try:
            sql_text = obfuscate_sql_with_metadata(
                sql_text, self._config.obfuscator_options, replace_null_character=True
            )['query']
        except Exception as e:
            sql_text = "ERROR: failed to obfuscate"
            if self._config.log_unobfuscated_queries:
                self._log.warning("Failed to obfuscate sql text within a deadlock=[%s] | err=[%s]", sql_text, e)
            else:
                self._log.warning("Failed to obfuscate sql text within a deadlock | err=[%s]", e)
        return sql_text

    def obfuscate_xml(self, root):
        process_list = root.find(".//process-list")
        if process_list is None:
            raise Exception("process-list element not found. The deadlock XML is in an unexpected format.")
        for process in process_list.findall('process'):
            for inputbuf in process.findall('.//inputbuf'):
                if inputbuf.text is not None:
                    inputbuf.text = self.obfuscate_no_except_wrapper(inputbuf.text)
            for frame in process.findall('.//frame'):
                if frame.text is not None:
                    frame.text = self.obfuscate_no_except_wrapper(frame.text)
        return

    def _collect_deadlocks(self):
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                self._log.debug("collecting sql server deadlocks")
                self._log.debug(
                    "Running query [%s] with max deadlocks %s and timestamp %s",
                    DETECT_DEADLOCK_QUERY,
                    self._max_deadlocks,
                    self._last_deadlock_timestamp,
                )
                cursor.execute(
                    DETECT_DEADLOCK_QUERY, (self._max_deadlocks, min(-60, self._last_deadlock_timestamp - time()))
                )
                results = cursor.fetchall()
                converted_xmls = []
                for result in results:
                    try:
                        root = ET.fromstring(result[1])
                    except Exception as e:
                        self._log.error(
                            """An error occurred while collecting SQLServer deadlocks.
                             One of the deadlock XMLs couldn't be parsed. The error: {}. XML: {}""".format(
                                e, result
                            )
                        )
                        continue
                    try:
                        self.obfuscate_xml(root)
                    except Exception as e:
                        error = "An error occurred while obfuscating SQLServer deadlocks. The error: {}".format(e)
                        self._log.error(error)
                        continue

                    converted_xmls.append(ET.tostring(root, encoding='unicode'))
                self._last_deadlock_timestamp = time()
                return converted_xmls

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_deadlocks(self):
        deadlock_xmls_collected = self._collect_deadlocks()
        deadlock_xmls = []
        total_number_of_characters = 0
        for i, deadlock in enumerate(deadlock_xmls_collected):
            total_number_of_characters += len(deadlock)
            if total_number_of_characters > self._deadlock_payload_max_bytes:
                self._log.warning(
                    """We've dropped {} deadlocks from a total of {} deadlocks as the
                     max deadlock payload of {} bytes was exceeded.""".format(
                        len(deadlock_xmls) - i, len(deadlock_xmls), self._deadlock_payload_max_bytes
                    )
                )
                break
            else:
                deadlock_xmls.append({"xml": deadlock})

        # Send payload only if deadlocks found
        if deadlock_xmls:
            deadlocks_event = self._create_deadlock_event(deadlock_xmls)
            payload = json.dumps(deadlocks_event, default=default_json_event_encoding)
            self._log.debug("Deadlocks payload: %s", str(payload))
            self._check.database_monitoring_query_activity(payload)

    def _create_deadlock_event(self, deadlock_xmls):
        event = {
            "host": self._check.resolved_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "sqlserver",
            "dbm_type": "deadlocks",
            "collection_interval": self.collection_interval,
            "ddtags": self.tags,
            "timestamp": time() * 1000,
            'sqlserver_version': self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            'sqlserver_engine_edition': self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            "cloud_metadata": self._config.cloud_metadata,
            "sqlserver_deadlocks": deadlock_xmls,
        }
        return event
    
    def run_job(self):
        self.collect_deadlocks()

