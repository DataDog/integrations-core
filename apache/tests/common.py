# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

CHECK_NAME = 'apache'

HERE = get_here()
HOST = get_docker_hostname()
PORT = '18180'
BASE_URL = "http://{0}:{1}".format(HOST, PORT)

STATUS_URL = "{0}/server-status".format(BASE_URL)
AUTO_STATUS_URL = "{0}?auto".format(STATUS_URL)

STATUS_CONFIG = {'apache_status_url': STATUS_URL, 'tags': ['instance:first'], 'disable_generic_tags': True}

AUTO_CONFIG = {'apache_status_url': AUTO_STATUS_URL, 'tags': ['instance:second'], 'disable_generic_tags': True}

BAD_CONFIG = {'apache_status_url': 'http://localhost:1234/server-status', 'disable_generic_tags': True}

NO_METRIC_CONFIG = {'apache_status_url': BASE_URL, 'disable_generic_tags': True}

APACHE_GAUGES = [
    'apache.performance.idle_workers',
    'apache.performance.busy_workers',
    'apache.performance.max_workers',
    'apache.performance.cpu_load',
    'apache.performance.uptime',
    'apache.net.bytes',
    'apache.net.hits',
    'apache.conns_total',
    'apache.conns_async_writing',
    'apache.conns_async_keep_alive',
    'apache.conns_async_closing',
    'apache.scoreboard.waiting_for_connection',
    'apache.scoreboard.starting_up',
    'apache.scoreboard.reading_request',
    'apache.scoreboard.sending_reply',
    'apache.scoreboard.keepalive',
    'apache.scoreboard.dns_lookup',
    'apache.scoreboard.closing_connection',
    'apache.scoreboard.logging',
    'apache.scoreboard.gracefully_finishing',
    'apache.scoreboard.idle_cleanup',
    'apache.scoreboard.open_slot',
    'apache.scoreboard.disabled',
]

APACHE_RATES = ['apache.net.bytes_per_s', 'apache.net.request_per_s']

APACHE_VERSION = os.getenv('APACHE_VERSION')
