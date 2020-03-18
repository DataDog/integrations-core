# (C) Datadog, Inc. 2013-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.base import PDHBaseCheck

EVENT_TYPE = SOURCE_TYPE_NAME = 'dotnetclr'

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


class DotnetclrCheck(PDHBaseCheck):
    def __init__(self, name, init_config, instances=None):
        PDHBaseCheck.__init__(self, name, init_config, instances=instances, counter_list=DEFAULT_COUNTERS)
