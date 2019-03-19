# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.dev import get_docker_hostname, get_here

CHECK_NAME = 'apache'

HERE = get_here()
HOST = get_docker_hostname()
PORT = '18180'
BASE_URL = "http://{0}:{1}".format(HOST, PORT)

STATUS_URL = "{0}/server-status".format(BASE_URL)
AUTO_STATUS_URL = "{0}?auto".format(STATUS_URL)

STATUS_CONFIG = {
    'apache_status_url': STATUS_URL,
    'tags': ['instance:first']
}

AUTO_CONFIG = {
    'apache_status_url': AUTO_STATUS_URL,
    'tags': ['instance:second']
}

BAD_CONFIG = {
    'apache_status_url': 'http://localhost:1234/server-status',
}

APACHE_GAUGES = [
    'apache.performance.idle_workers',
    'apache.performance.busy_workers',
    'apache.performance.cpu_load',
    'apache.performance.uptime',
    'apache.net.bytes',
    'apache.net.hits',
    'apache.conns_total',
    'apache.conns_async_writing',
    'apache.conns_async_keep_alive',
    'apache.conns_async_closing'
]

APACHE_RATES = [
    'apache.net.bytes_per_s',
    'apache.net.request_per_s'
]
