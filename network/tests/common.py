# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.dev import get_here

HERE = get_here()
SERVICE_CHECK_NAME = "network"

INSTANCE = {"collect_connection_state": True}

INSTANCE_BLACKLIST = {"collect_connection_state": True, "blacklist_conntrack_metrics": ["count"]}


# In order to collect connection state we need `ss` command included in `iproute2` package
E2E_METADATA = {'start_commands': ['apt-get update', 'apt-get install iproute2 -y']}

EXPECTED_METRICS = [
    'system.net.bytes_rcvd',
    'system.net.bytes_sent',
    'system.net.packets_in.count',
    'system.net.packets_in.error',
    'system.net.packets_out.count',
    'system.net.packets_out.error',
]

E2E_EXPECTED_METRICS = EXPECTED_METRICS + [
    "system.net.tcp4.closing",
    "system.net.tcp4.established",
    "system.net.tcp4.listening",
    "system.net.tcp4.opening",
    "system.net.tcp4.time_wait",
    "system.net.tcp6.closing",
    "system.net.tcp6.established",
    "system.net.tcp6.listening",
    "system.net.tcp6.opening",
    "system.net.tcp6.time_wait",
    "system.net.udp4.connections",
    "system.net.udp6.connections",
]

CONNTRACK_METRICS = [
    'system.net.conntrack.acct',
    'system.net.conntrack.buckets',
    'system.net.conntrack.checksum',
    'system.net.conntrack.events',
    'system.net.conntrack.expect_max',
    'system.net.conntrack.generic_timeout',
    'system.net.conntrack.helper',
    'system.net.conntrack.log_invalid',
    'system.net.conntrack.max',
    'system.net.conntrack.tcp_loose',
    'system.net.conntrack.tcp_max_retrans',
    'system.net.conntrack.tcp_timeout_close',
    'system.net.conntrack.tcp_timeout_close_wait',
    'system.net.conntrack.tcp_timeout_established',
    'system.net.conntrack.tcp_timeout_fin_wait',
    'system.net.conntrack.tcp_timeout_last_ack',
    'system.net.conntrack.tcp_timeout_max_retrans',
    'system.net.conntrack.tcp_timeout_syn_recv',
    'system.net.conntrack.tcp_timeout_syn_sent',
    'system.net.conntrack.tcp_timeout_time_wait',
    'system.net.conntrack.tcp_timeout_unacknowledged',
    'system.net.conntrack.timestamp',
]
