# (C) Datadog, Inc. 2013-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# datadog
from datadog_checks.checks.win import PDHBaseCheck

EVENT_TYPE = SOURCE_TYPE_NAME = 'dotnetclr'

DEFAULT_COUNTERS = [
    # counterset, instance of counter, counter name, metric name
    # This set is from the Microsoft recommended counters to monitor exchange:
    # https://technet.microsoft.com/en-us/library/dn904093%28v=exchg.150%29.aspx?f=255&MSPPError=-2147217396

    # .NET Exceptions counters
    [".NET CLR Exceptions", None, "# of Exceps Thrown / sec", "dotnetclr.exceptions.thrown_persec", "gauge"],  # noqa: E501

    # .NET Framework counters
    [".NET CLR Memory",     None, "% Time in GC",             "dotnetclr.memory.time_in_gc",           "gauge"],  # noqa: E501
    [".NET CLR Memory",     None, "# Total committed Bytes",  "dotnetclr.memory.committed.heap_bytes", "gauge"],  # noqa: E501
    [".NET CLR Memory",     None, "# Total reserved Bytes",   "dotnetclr.memory.reserved.heap_bytes",  "gauge"],  # noqa: E501
]


class DotnetclrCheck(PDHBaseCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        PDHBaseCheck.__init__(self, name, init_config, agentConfig, instances=instances, counter_list=DEFAULT_COUNTERS)
