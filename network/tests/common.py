# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.dev import get_here

HERE = get_here()
SERVICE_CHECK_NAME = "network"

INSTANCE = {
    "collect_connection_state": True,
}

EXPECTED_METRICS = [
    'system.net.bytes_rcvd',
    'system.net.bytes_sent',
    'system.net.packets_in.count',
    'system.net.packets_in.error',
    'system.net.packets_out.count',
    'system.net.packets_out.error',
]
