# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
METRICS_CONFIG = {
    '.NET CLR Exceptions': {'name': 'exceptions', 'counters': [{'# of Exceps Thrown / sec': 'thrown_persec'}]},
    '.NET CLR Memory': {
        'name': 'memory',
        'counters': [
            {
                '% Time in GC': 'time_in_gc',
                '# Total committed Bytes': 'committed.heap_bytes',
                '# Total reserved Bytes': 'reserved.heap_bytes',
            }
        ],
    },
}

DEFAULT_COUNTERS = [
    # counterset, instance of counter, counter name, metric name
    # This set is from the Microsoft recommended counters to monitor exchange:
    # https://technet.microsoft.com/en-us/library/dn904093%28v=exchg.150%29.aspx?f=255&MSPPError=-2147217396
    # .NET Exceptions counters
    [".NET CLR Exceptions", None, "# of Exceps Thrown / sec", "dotnetclr.exceptions.thrown_persec", "gauge"],
    # .NET Framework counters
    [".NET CLR Memory", None, "% Time in GC", "dotnetclr.memory.time_in_gc", "gauge"],
    [".NET CLR Memory", None, "# Total committed Bytes", "dotnetclr.memory.committed.heap_bytes", "gauge"],
    [".NET CLR Memory", None, "# Total reserved Bytes", "dotnetclr.memory.reserved.heap_bytes", "gauge"],
]
