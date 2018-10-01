# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
from datadog_checks.utils.common import get_docker_hostname

CHECK_NAME = "go_expvar"
HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
PORT = '8079'

URL = 'http://{}:{}'.format(HOST, PORT)

GO_EXPVAR_URL_PATH = "/debug/vars"

URL_WITH_PATH = "{}{}".format(URL, GO_EXPVAR_URL_PATH)

INSTANCE = {
    "expvar_url": URL,
    'tags': ['my_tag'],
    'metrics': [
        {
            'path': 'num_calls',
            "type": "rate"
        },
    ]
}

CHECK_GAUGES = [
    'go_expvar.memstats.alloc',
    'go_expvar.memstats.heap_alloc',
    'go_expvar.memstats.heap_idle',
    'go_expvar.memstats.heap_inuse',
    'go_expvar.memstats.heap_objects',
    'go_expvar.memstats.heap_released',
    'go_expvar.memstats.heap_sys',
    'go_expvar.memstats.total_alloc',
]

# this is a histogram
CHECK_GAUGES_DEFAULT = [
    'go_expvar.memstats.pause_ns',
]

CHECK_RATES = [
    'go_expvar.memstats.frees',
    'go_expvar.memstats.lookups',
    'go_expvar.memstats.mallocs',
    'go_expvar.memstats.num_gc',
    'go_expvar.memstats.pause_total_ns',
]
