# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import get_here
from datadog_checks.teleport import TeleportCheck

pytestmark = [pytest.mark.unit]

PROXY_METRICS = [
    "proxy.failed_connect_to_node_attempts",
    "proxy.failed_login_attempts",
    "proxy.grpc.client.started",
    "proxy.grpc.client.handled",
    "proxy.grpc.client.msg_received",
    "proxy.grpc.client.msg_sent",
    "proxy.grpc.server_handled_total",
    "proxy.grpc.server_msg_received_total",
    "proxy.grpc.server_msg_sent_total",
    "proxy.grpc.server_started_total",
    "proxy.connection_limit_exceeded",
    "proxy.peer_client_dial_error",
    "proxy.peer_server_connections",
    "proxy.peer_client_rpc",
    "proxy.peer_client_rpc_total",
    "proxy.peer_client_rpc_duration_seconds",
    "proxy.peer_client_message_sent_size",
    "proxy.peer_client_message_received_size",
    "proxy.peer_server_rpc",
    "proxy.peer_server_rpc_duration_seconds",
    "proxy.peer_server_message_sent_size",
    "proxy.peer_server_message_received_size",
    "proxy.ssh_sessions_total",
    "proxy.missing_ssh_tunnels",
    "proxy.remote_clusters",
    "proxy.teleport_connect_to_node_attempts",
    "proxy.teleport_reverse_tunnels_connected",
    "proxy.trusted_clusters",
    "proxy.teleport_proxy_db_connection_setup_time_seconds",
    "proxy.teleport_proxy_db_connection_dial_attempts",
    "proxy.teleport_proxy_db_connection_dial_failures",
    "proxy.teleport_proxy_db_attempted_servers_total",
    "proxy.teleport_proxy_db_connection_tls_config_time_seconds",
    "proxy.teleport_proxy_db_active_connections_total",
]

def test_proxy_teleport_metrics(dd_run_check, aggregator, mock_http_response):
    fixtures_path = os.path.join(get_here(), 'fixtures', 'metrics.txt')
    mock_http_response(file_path=fixtures_path)

    instance = {"diagnostic_url": "http://hostname:3000"}
    check = TeleportCheck('teleport', {}, [instance])
    dd_run_check(check)

    for metric in PROXY_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
