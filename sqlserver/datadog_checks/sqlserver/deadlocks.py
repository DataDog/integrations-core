# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import xml.etree.ElementTree as ET
from datetime import datetime
from time import time

from datadog_checks.base.utils.db.utils import obfuscate_sql_with_metadata
from datadog_checks.sqlserver.queries import DETECT_DEADLOCK_QUERY


MAX_DEADLOCKS = 100


class Deadlocks:

    def __init__(self, check, conn_prefix, config):
        self._check = check
        self._log = self._check.log
        self._conn_key_prefix = conn_prefix
        self._config = config
        self._last_deadlock_timestamp = time()
        self._max_deadlocks = config.deadlocks_config.get("max_deadlocks", MAX_DEADLOCKS)

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
            return "process-list element not found. The deadlock XML is in an unexpected format."
        for process in process_list.findall('process'):
            for inputbuf in process.findall('.//inputbuf'):
                if inputbuf.text is not None:
                    inputbuf.text = self.obfuscate_no_except_wrapper(inputbuf.text)
            for frame in process.findall('.//frame'):
                if frame.text is not None:
                    frame.text = self.obfuscate_no_except_wrapper(frame.text)
        return None

    def collect_deadlocks(self):
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                self._log.debug("collecting sql server deadlocks")
                self._log.debug(
                    "Running query [%s] with max deadlocks %s and timestamp %s",
                    DETECT_DEADLOCK_QUERY,
                    self._max_deadlocks,
                    self._last_deadlock_timestamp,
                )
                cursor.execute(DETECT_DEADLOCK_QUERY, (self._max_deadlocks, min(-60, self._last_deadlock_timestamp - time())))
                results = cursor.fetchall()
                last_deadlock_datetime = time()
                converted_xmls = []
                errors = []
                for result in results:
                    try:
                        root = ET.fromstring(result[1])
                    except Exception as e:
                        self._log.error(
                            """An error occurred while collecting SQLServer deadlocks.
                             One of the deadlock XMLs couldn't be parsed. The error: {}""".format(
                                e
                            )
                        )
                        errors.append("Truncated deadlock xml - {}".format(result[:50]))
                        continue
                    error = self.obfuscate_xml(root)
                    if not error:
                        converted_xmls.append(ET.tostring(root, encoding='unicode'))
                    else:
                        errors.append(error)
                self._last_deadlock_timestamp = time()
                return converted_xmls, errors
