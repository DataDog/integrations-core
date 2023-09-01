# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Not used by tests, but can be manually run to generate the mock_results.json file.
import json
import random
import string
import time
from math import log

MAPPING = {
    'COMMANDLOG': ['timestamp', 'host_id', 'hostname', 'int', 'int', 'int', 'int', 'int'],
    'CPU': ['timestamp', 'host_id', 'hostname', 'percent'],
    'EXPORT': [
        'timestamp',
        'host_id',
        'hostname',
        'site_id',
        'partition_id',
        'str',
        'str',
        'str',
        'int',
        'int',
        'timestamp',
        'timestamp',
        'int',
        'int',
        'int',
        'str',
    ],
    'GC': ['timestamp', 'host_id', 'hostname', 'int', 'int', 'int', 'int'],
    'IDLETIME': ['timestamp', 'host_id', 'hostname', 'site_id', 'int', 'percent', 'int', 'int', 'int', 'int'],
    'IMPORT': ['timestamp', 'host_id', 'hostname', 'site_id', 'str', 'str', 'int', 'int', 'int', 'int'],
    'INDEX': [
        'timestamp',
        'host_id',
        'hostname',
        'site_id',
        'partition_id',
        'str',
        'str',
        'str',
        'bool',
        'bool',
        'int',
        'int',
    ],
    'IOSTATS': ['timestamp', 'host_id', 'hostname', 'int', 'str', 'int', 'int', 'int', 'int'],
    'LATENCY': [
        'timestamp',
        'host_id',
        'hostname',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
    ],
    'MEMORY': [
        'timestamp',
        'host_id',
        'hostname',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
    ],
    'PROCEDURE': [
        'timestamp',
        'host_id',
        'hostname',
        'site_id',
        'partition_id',
        'str',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'bool',
    ],
    'PROCEDUREOUTPUT': ['timestamp', 'str', 'int', 'int', 'int', 'int', 'int', 'int'],
    'PROCEDUREPROFILE': ['timestamp', 'str', 'int', 'int', 'int', 'int', 'int', 'int', 'int'],
    'QUEUE': ['timestamp', 'host_id', 'hostname', 'site_id', 'int', 'int', 'int', 'int'],
    'SNAPSHOTSTATUS': [
        'timestamp',
        'host_id',
        'hostname',
        'str',
        'str',
        'str',
        'str',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
        'str',
        'str',
    ],
    'TABLE': [
        'timestamp',
        'host_id',
        'hostname',
        'site_id',
        'partition_id',
        'str',
        'str',
        'int',
        'int',
        'int',
        'int',
        'int',
        'int',
    ],
}


def generate_host_id(idx=0):
    return str(idx)


def generate_hostname(idx=0):
    return "voltdb-host-%d" % idx


def generate_site_id(idx=0):
    return idx


def generate_partition_id(idx=0):
    return idx


def generate_bool(idx=0):
    return idx % 2 == 0


def generate_int(idx=0):
    return int(-(idx * 10 + 1) * 100000 * log(1 - random.random(), 2))


def generate_timestamp(idx=0):
    yesterday = time.time() - 24 * 60 * 60
    yesterday -= random.random() * 3600
    # yesterday is between 24h and 25h ago
    yesterday += idx * 3600

    return int(yesterday * 1000)


def generate_percent(idx=0):
    return random.random()


def generate_str(idx=0):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(15)) + "-" + str(idx)


def generate_data(cnt=1):
    data = {}

    for component in MAPPING.keys():
        data[component] = []
        for idx in range(cnt):
            tmp_data = []
            for elem_type in MAPPING[component]:
                tmp_data.append(globals()['generate_%s' % elem_type](idx))
            data[component].append(tmp_data)
    return data


with open('mock_results.json', 'w') as f:
    json.dump(generate_data(3), f, indent=4)
