# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import xml.etree.ElementTree as ET
from time import time

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.config import SQLServerConfig
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION
from datadog_checks.sqlserver.queries import DEADLOCK_TIMESTAMP_ALIAS, DEADLOCK_XML_ALIAS, get_deadlocks_query

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

DEFAULT_COLLECTION_INTERVAL = 600
MAX_DEADLOCKS = 100
MAX_PAYLOAD_BYTES = 19e6

PAYLOAD_TIMESTAMP = "deadlock_timestamp"
PAYLOAD_QUERY_SIGNATURE = "query_signatures"
PAYLOAD_XML = "xml"


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
        self._convert_xml_to_str = False
        # MSOLEDB drivers don't properly support SQL Server XML data type,
        # so we need to convert it to string before returning it to the Agent.
        if self._check.connection is not None and self._check.connection.connector != "odbc":
            self._convert_xml_to_str = True
        super(Deadlocks, self).__init__(
            check,
            run_sync=True,
            enabled=self._config.deadlocks_config.get('enabled', False),
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
            error_text = "Failed to obfuscate sql text within a deadlock"
            if self._config.log_unobfuscated_queries:
                error_text += "=[%s]" % sql_text
            error_text += " | err=[%s]"
            self._log.error(error_text, e)
        return sql_text

    def _obfuscate_xml(self, root):
        process_list = root.find(".//process-list")
        if process_list is None:
            raise Exception("process-list element not found. The deadlock XML is in an unexpected format.")
        query_signatures = []
        for process in process_list.findall('process'):
            for inputbuf in process.findall('.//inputbuf'):
                if inputbuf.text is not None:
                    inputbuf.text = self.obfuscate_no_except_wrapper(inputbuf.text)
                    spid = process.get('spid')
                    if spid is not None:
                        try:
                            spid = int(spid)
                        except ValueError:
                            self._log.error("spid not an integer. Skipping query signature computation.")
                            continue
                        if spid in query_signatures:
                            continue
                        query_signatures.append({"spid": spid, "signature": compute_sql_signature(inputbuf.text)})
                    else:
                        self._log.error("spid not found in process element. Skipping query signature computation.")
            for frame in process.findall('.//frame'):
                if frame.text is not None:
                    frame.text = self.obfuscate_no_except_wrapper(frame.text)
        return query_signatures

    def _get_lookback_seconds(self):
        return min(-60, self._last_deadlock_timestamp - time())

    def _query_deadlocks(self):
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                self._log.debug("collecting sql server deadlocks")
                self._log.debug(
                    "Running query [%s] with max deadlocks %s and timestamp %s",
                    get_deadlocks_query(),
                    self._max_deadlocks,
                    self._last_deadlock_timestamp,
                )
                try:
                    cursor.execute(get_deadlocks_query(), (self._max_deadlocks, self._get_lookback_seconds()))
                except Exception as e:
                    if "Data column of Unknown ADO type" in str(e):
                        raise Exception(f"{str(e)} | cursor.description: {cursor.description}")
                    raise e

                columns = [column[0] for column in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _create_deadlock_rows(self):
        db_rows = self._query_deadlocks()
        deadlock_events = []
        total_number_of_characters = 0
        for i, row in enumerate(db_rows):
            try:
                root = ET.fromstring(row[DEADLOCK_XML_ALIAS])
            except Exception as e:
                self._log.error(
                    """An error occurred while collecting SQLServer deadlocks.
                        One of the deadlock XMLs couldn't be parsed. The error: {}. XML: {}""".format(
                        e, row
                    )
                )
                continue
            query_signatures = {}
            try:
                query_signatures = self._obfuscate_xml(root)
            except Exception as e:
                error = "An error occurred while obfuscating SQLServer deadlocks. The error: {}".format(e)
                self._log.error(error)
                continue

            total_number_of_characters += len(row) + len(query_signatures)
            if total_number_of_characters > self._deadlock_payload_max_bytes:
                self._log.warning(
                    """We've dropped {} deadlocks from a total of {} deadlocks as the
                     max deadlock payload of {} bytes was exceeded.""".format(
                        len(db_rows) - i, len(db_rows), self._deadlock_payload_max_bytes
                    )
                )
                break

            deadlock_events.append(
                {
                    PAYLOAD_TIMESTAMP: row[DEADLOCK_TIMESTAMP_ALIAS],
                    PAYLOAD_XML: ET.tostring(root, encoding='unicode'),
                    PAYLOAD_QUERY_SIGNATURE: query_signatures,
                }
            )
        self._last_deadlock_timestamp = time()
        return deadlock_events

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_deadlocks(self):
        rows = self._create_deadlock_rows()
        # Send payload only if deadlocks found
        if rows:
            deadlocks_event = self._create_deadlock_event(rows)
            payload = json.dumps(deadlocks_event, default=default_json_event_encoding)
            self._log.debug("Deadlocks payload: %s", str(payload))
            self._check.database_monitoring_query_activity(payload)

    def _create_deadlock_event(self, deadlock_rows):
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
            "sqlserver_deadlocks": deadlock_rows,
        }
        return event

    def run_job(self):
        self.collect_deadlocks()
