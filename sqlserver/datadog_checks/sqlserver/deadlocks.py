# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import xml.etree.ElementTree as ET
from datetime import datetime

from datadog_checks.sqlserver.queries import (
    DETECT_DEADLOCK_QUERY,
)

import pdb

class Deadlocks:


    def __init__(self, check, config, conn_prefix, obfuscate_sql):
        #may be dont need a check
        self._check = check
        self._log = check.log
        self._conn_key_prefix = conn_prefix
        self._obfuscate_sql = obfuscate_sql
        self._last_deadlock_timestamp = '1900-07-01 00:00:26.363'
        
    def obfuscate_xml(self, root):
        s= ET.tostring(root, encoding='unicode')
        print(s)
        process_list = root.find(".//process-list")

        # Iterate through <process> elements and apply function F
        for process in process_list.findall('process'):
            inputbuf = process.find('inputbuf')
            inputbuf.text = self._obfuscate_sql(inputbuf.text)['query']
            for frame in process.findall('.//frame'):
                frame.text = self._obfuscate_sql(frame.text)['query']
        print(s)
        

    def collect_deadlocks(self):
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                #todo check if 0 works or needs to be converted to 0.0.0 etc ... '2024-07-31 15:05:26.363'
                time_offset = self._last_deadlock_timestamp
                cursor.execute(DETECT_DEADLOCK_QUERY, (time_offset,))
                results = cursor.fetchall()
                last_deadlock_datetime = datetime.strptime(self._last_deadlock_timestamp, '%Y-%m-%d %H:%M:%S.%f')
                converted_xmls = []
                for result in results:
                    root = ET.fromstring(result[1])
                    datetime_obj = datetime.strptime(root.get('timestamp'), '%Y-%m-%dT%H:%M:%S.%fZ')
                    if last_deadlock_datetime < datetime_obj:
                        last_deadlock_datetime = datetime_obj
                    #apply obfuscator loop throur resources 
                    self.obfuscate_xml(root)
                    s= ET.tostring(root, encoding='unicode')
                    print(s)
                    converted_xmls.append(ET.tostring(root, encoding='unicode'))
                #TODO check conversion doesnt loose precision
                self._last_deadlock_timestamp = last_deadlock_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
                print(converted_xmls)
                return converted_xmls    
                #todo extract timestamp if any

                #put int da event 




# Parse the XML data
#root = ET.fromstring(xml_data)

# Extract the timestamp attribute
#timestamp = root.get('timestamp')
#obfuscate , serialize in text or compress ?
#print("Timestamp:", timestamp)
