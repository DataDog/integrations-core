# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.dev import get_here

HERE = get_here()
SERVICE_CHECK_NAME = "network"

INSTANCE = {"collect_connection_state": True}

EXPECTED_METRICS = [
    'system.net.bytes_rcvd',
    'system.net.bytes_sent',
    'system.net.packets_in.count',
    'system.net.packets_in.error',
    'system.net.packets_out.count',
    'system.net.packets_out.error',
]

CONNTRACK_METRICS = [
    'system.net.conntrack.acct',
    'system.net.conntrack.buckets',
    'system.net.conntrack.checksum',
    'system.net.conntrack.count',
    'system.net.conntrack.drop',
    'system.net.conntrack.early_drop',
    'system.net.conntrack.error',
    'system.net.conntrack.events',
    'system.net.conntrack.expect_max',
    'system.net.conntrack.found',
    'system.net.conntrack.generic_timeout',
    'system.net.conntrack.helper',
    'system.net.conntrack.ignore',
    'system.net.conntrack.invalid',
    'system.net.conntrack.insert',
    'system.net.conntrack.insert_failed',
    'system.net.conntrack.log_invalid',
    'system.net.conntrack.max',
    'system.net.conntrack.search_restart',
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
