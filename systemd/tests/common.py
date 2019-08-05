# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

HERE = os.path.dirname(os.path.abspath(__file__))


INSTANCE = {'unit_names': ['dbus.service', 'dbus.socket'], 'tags': ['test:e2e']}

UNIT_METRICS = ['systemd.unit.uptime', 'systemd.unit.loaded', 'systemd.unit.active']

SOCKET_METRICS = ['systemd.socket.n_connections', 'systemd.socket.n_accepted']

SERVICE_METRICS = [
    'systemd.service.memory_current',
    'systemd.service.tasks_current',
    # centos/systemd:latest contains systemd v219, it does not contain CPUUsageNSec and NRestarts yet
    # 'systemd.service.cpu_usage_n_sec',
    # 'systemd.service.n_restarts',
]

AGGREGATE_UNIT_METRICS = ['systemd.unit.count', 'systemd.unit.loaded.count']

ALL_METRICS = UNIT_METRICS + SOCKET_METRICS + AGGREGATE_UNIT_METRICS + SERVICE_METRICS
