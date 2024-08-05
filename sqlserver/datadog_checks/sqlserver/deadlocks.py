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
import time

class Deadlocks:

    def __init__(self, check, conn_prefix, config):
        self._check = check
        self._log = self._check.log
        self._conn_key_prefix = conn_prefix
        self._config = config
        self._last_deadlock_timestamp = '1900-01-01 01:01:01.111'
        
    def obfuscate_xml(self, root):
        # TODO put exception here if not found as this would signal in a format change
        process_list = root.find(".//process-list")
        for process in process_list.findall('process'):
            inputbuf = process.find('inputbuf')
            inputbuf.text = obfuscate_sql_with_metadata(inputbuf.text, self._config.obfuscator_options, replace_null_character=True)['query']
            for frame in process.findall('.//frame'):
                frame.text = obfuscate_sql_with_metadata(frame.text, self._config.obfuscator_options, replace_null_character=True)['query']

    def collect_deadlocks(self):
        pdb.set_trace()
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                #Q test this query for 1000 deadlocks ? speed , truncation ? 
                #Q shell we may be limit amount of data, 1000 deadlock is 4MB but do we need more than .. 50 ?(conf parameter)
                cursor.execute(DETECT_DEADLOCK_QUERY, (self._last_deadlock_timestamp,))
                results = cursor.fetchall()
                last_deadlock_datetime = datetime.strptime(self._last_deadlock_timestamp, '%Y-%m-%d %H:%M:%S.%f')
                converted_xmls = []
                for result in results:
                    #TODO if this fails  what we do , can be obfuscate it or just drop and notify backend? 
                    #TODO speed of serialization deciarialization
                    try:
                        root = ET.fromstring(result[1])
                    except Exception as e:
                        #TODO notify backend ? try to check manually for process list tag and processes 
                        # say if we can find <process> and </process> and <frame> and </frame> we could 
                        # still try to do something but my feeling just to notify backend 

                        # Other thing do we want to suggest to set ring buffer to 1MB ? 
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
