# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

INSTANCE = {
    'class': 'Win32_PerfFormattedData_PerfProc_Process',
    'metrics': [
        ['ThreadCount', 'proc.threads.count', 'gauge'],
        ['IOReadBytesPerSec', 'proc.io.bytes_read', 'gauge'],
        ['VirtualBytes', 'proc.mem.virtual', 'gauge'],
        ['PercentProcessorTime', 'proc.cpu_pct', 'gauge'],
    ],
    'tag_by': 'Name',
}

INSTANCE_METRICS = [
    'proc.threads.count',
    'proc.io.bytes_read',
    'proc.mem.virtual',
    'proc.cpu_pct',
]

WMI_CONFIG = {
    'class': 'Win32_PerfFormattedData_PerfDisk_LogicalDisk',
    'metrics': [
        ['AvgDiskBytesPerWrite', 'winsys.disk.avgdiskbytesperwrite', 'gauge'],
        ['FreeMegabytes', 'winsys.disk.freemegabytes', 'gauge']
    ],
    'tag_by': 'Name',
    'constant_tags': ['foobar'],
}
