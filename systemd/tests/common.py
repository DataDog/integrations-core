# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()

INSTANCE = {
    'unit_names': [
        'dbus.service',
        'dbus.socket',
    ],
    'tags': ['test:e2e'],
}

UNIT_METRICS = [
    'systemd.unit.uptime',
    'systemd.unit.loaded',
    'systemd.unit.active',
]

SOCKET_METRICS = [
    'systemd.socket.n_connections',
    'systemd.socket.n_accepted',
]

SERVICE_METRICS = [
    'systemd.service.cpu_usage_n_sec',
    'systemd.service.memory_current',
    'systemd.service.tasks_current',
    'systemd.service.n_restarts',
]

ALL_UNIT_METRICS = [
    'systemd.unit.count',
    'systemd.unit.loaded.count'
]
