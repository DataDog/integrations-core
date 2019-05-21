# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()

# ID
CONTAINER_NAME = "dd-test-cacti"

RRD_PATH = '/var/lib/cacti/rra'

INSTANCE_INTEGRATION = {'mysql_host': 'localhost',
                        'mysql_user': 'cactiuser',
                        'mysql_password': 'cactipass',
                        'rrd_path': RRD_PATH,
                        'collect_task_metrics': True}

EXPECTED_METRICS = [
    'cacti.hosts.count',
    'cacti.metrics.count',
    'cacti.rrd.count',
    'system.disk.free.last',
    'system.disk.free.max',
    'system.disk.free.min',
    'system.disk.used.last',
    'system.disk.used.max',
    'system.disk.used.min',
    'system.load.1.last',
    'system.load.1.max',
    'system.load.1.min',
    'system.load.15.last',
    'system.load.15.max',
    'system.load.15.min',
    'system.load.5.last',
    'system.load.5.max',
    'system.load.5.min',
    'system.mem.buffered.last',
    'system.mem.buffered.max',
    'system.mem.buffered.min',
    'system.ping.latency,gauge',
    'system.ping.latency.max',
    'system.proc.running.last',
    'system.proc.running.max',
    'system.proc.running.min',
    'system.swap.free.max',
    'system.users.current.last',
    'system.users.current.max',
    'system.users.current.min',
]

E2E_METADATA = {
    'start_commands': [
        'apt-get update',
        'apt-get install rrdtool librrd-dev libpython-dev build-essential -y',
        'pip install rrdtool'
    ]
}