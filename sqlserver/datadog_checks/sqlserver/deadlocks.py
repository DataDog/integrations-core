# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import xml.etree.ElementTree as ET
from datetime import datetime

from datadog_checks.base.utils.db.utils import obfuscate_sql_with_metadata

from datadog_checks.sqlserver.queries import (
    DETECT_DEADLOCK_QUERY,
)
#TODO temp imports:
import pdb

MAX_DEADLOCKS = 100

class Deadlocks:

    def __init__(self, check, conn_prefix, config):
        self._check = check
        self._log = self._check.log
        self._conn_key_prefix = conn_prefix
        self._config = config
        self._last_deadlock_timestamp = '1900-01-01 01:01:01.111'
        self._max_deadlocks = config.deadlocks_config.get("max_deadlocks", MAX_DEADLOCKS)


    def obfuscate_no_except_wrapper(self, sql_text):
        try:
            sql_text = obfuscate_sql_with_metadata(sql_text, self._config.obfuscator_options, replace_null_character=True)['query']
        except Exception as e:
            if self._config.log_unobfuscated_queries:
                self.log.warning("Failed to obfuscate sql text within a deadlock=[%s] | err=[%s]", sql_text, e)
            else:
                self.log.debug("Failed to obfuscate sql text within a deadlock | err=[%s]", e)
            sql_text = "ERROR: failed to obfuscate"
        return sql_text

    def obfuscate_xml(self, root):
        # TODO put exception here if not found as this would signal in a format change
        pdb.set_trace()
        process_list = root.find(".//process-list")
        for process in process_list.findall('process'):
            inputbuf = process.find('inputbuf')
            #TODO inputbuf.text can be truncated, check when live ?
            inputbuf.text = self.obfuscate_no_except_wrapper(inputbuf.text)
            for frame in process.findall('.//frame'):
                frame.text = self.obfuscate_no_except_wrapper(frame.text)

    def collect_deadlocks(self):
        pdb.set_trace()
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                cursor.execute(DETECT_DEADLOCK_QUERY, (self._max_deadlocks, self._last_deadlock_timestamp))
                results = cursor.fetchall()
                last_deadlock_datetime = datetime.strptime(self._last_deadlock_timestamp, '%Y-%m-%d %H:%M:%S.%f')
                converted_xmls = []
                for result in results:
                    try:
                        root = ET.fromstring(result[1])
                    except Exception as e:
                        # Other thing do we want to suggest to set ring buffer to 1MB ? 
                        # TODO notify backend ? How ? make a collection_errors array like in metadata json
                        self._log.error(
                        """An error occurred while collecting SQLServer deadlocks. 
                                One of the deadlock XMLs couldn't be parsed. The error: {}""".format(e)
                        )

                    datetime_obj = datetime.strptime(root.get('timestamp'), '%Y-%m-%dT%H:%M:%S.%fZ')
                    if last_deadlock_datetime < datetime_obj:
                        last_deadlock_datetime = datetime_obj
                    self.obfuscate_xml(root)
                    converted_xmls.append(ET.tostring(root, encoding='unicode'))
                self._last_deadlock_timestamp = last_deadlock_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
                pdb.set_trace()
                return converted_xmls
