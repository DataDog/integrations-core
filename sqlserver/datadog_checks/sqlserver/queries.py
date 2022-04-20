# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

QUERY_SERVER_STATIC_INFO = {
    'name': 'sys.dm_os_sys_info',
    'query': """
        SELECT (os.ms_ticks/1000) AS [Server Uptime]
        ,os.cpu_count AS [CPU Count]
        ,(os.physical_memory_kb*1024) AS [Physical Memory Bytes]
        ,os.virtual_memory_kb AS [Virtual Memory Bytes]
        ,(os.committed_kb*1024) AS [Total Server Memory Bytes]
        ,(os.committed_target_kb*1024) AS [Target Server Memory Bytes]
      FROM sys.dm_os_sys_info os""".strip(),
    'columns': [
        {'name': 'server.uptime', 'type': 'gauge'},
        {'name': 'server.cpu_count', 'type': 'gauge'},
        {'name': 'server.physical_memory', 'type': 'gauge'},
        {'name': 'server.virtual_memory', 'type': 'gauge'},
        {'name': 'server.committed_memory', 'type': 'gauge'},
        {'name': 'server.target_memory', 'type': 'gauge'},
    ]
}
