# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

RESOURCE_TYPES = {
    'cluster': {
        'plural': None,
    },
    'forest': {
        'plural': 'forests',
    },
    'database': {
        'plural': 'databases',
    },
    'host': {
        'plural': 'hosts',
    },
    'server': {
        'plural': 'servers',
    },
}

GAUGE_UNITS = [
    '%',
    'hits/sec',
    'locks/sec',
    'MB',
    'MB/sec',
    'misses/sec',
    'quantity',
    'quantity/sec',
    'sec',
    'sec/sec',
]
