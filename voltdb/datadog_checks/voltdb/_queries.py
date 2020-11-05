# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatcpu
CPUMetrics = {
    'name': 'cpu',
    'query': 'CPU',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        None,  # HOSTNAME
        {'name': 'cpu.percent_used', 'type': 'gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatmemory
MemoryMetrics = {
    'name': 'memory',
    'query': 'MEMORY',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        None,  # HOSTNAME
        {'name': 'memory.rss', 'type': 'gauge'},
        {'name': 'memory.java.used', 'type': 'gauge'},
        {'name': 'memory.java.unused', 'type': 'gauge'},
        {'name': 'memory.java.max_heap', 'type': 'gauge'},
        {'name': 'memory.tuple.data', 'type': 'gauge'},
        {'name': 'memory.tuple.allocated', 'type': 'gauge'},
        {'name': 'memory.tuple.count', 'type': 'gauge'},
        {'name': 'memory.index_memory', 'type': 'gauge'},
        {'name': 'memory.string_memory', 'type': 'gauge'},
        {'name': 'memory.pooled_memory', 'type': 'gauge'},
        {'name': 'memory.physical_memory', 'type': 'gauge'},
    ],
}

# COMPONENTS = [
#     "CPU",
#     "DRCONSUMER",
#     "DRPRODUCER",
#     "DRROLE",
#     "EXPORT",
#     "GC",
#     "IDLETIME",
#     "IMPORT",
#     "INDEX",
#     "INITIATOR",
#     "IOSTATS",
#     "LATENCY",
#     "LIVECLIENTS",
#     "MEMORY",
#     "PARTITIONCOUNT",
#     "PLANNER",
#     "PROCEDUREDETAIL",
#     "PROCEDUREINPUT",
#     "PROCEDUREOUTPUT",
#     "PROCEDUREPROFILE",
#     "QUEUE",
#     "REBALANCE",
#     "SNAPSHOTSTATUS",
#     "TABLE",
#     "TASK",
#     "TTL",
# ]
