# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


CHECK_NAME = 'pdh_check'

INSTANCE = {
    'countersetname': 'System',
    'metrics': [
        ['File Read Operations/sec', 'pdh.system.file_read_per_sec', 'gauge'],
        ['File Write Bytes/sec', 'pdh.system.file_write_bytes_sec', 'gauge'],
    ],
}

INSTANCE_METRICS = ['pdh.system.file_read_per_sec', 'pdh.system.file_write_bytes_sec']
