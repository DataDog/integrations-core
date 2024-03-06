# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import get_here
from datadog_checks.teleport import TeleportCheck

pytestmark = [pytest.mark.unit]

PROXY_METRICS = [
    "proxy.failed_connect_to_node_attempts.count",
    "proxy.failed_login_attempts.count",
    "proxy.grpc.client.started.count",
    "proxy.grpc.client.handled.count",
    "proxy.grpc.client.msg_received.count",
    "proxy.grpc.client.msg_sent.count",
    "proxy.connection_limit_exceeded.count",
    "proxy.peer_client.dial_error.count",
    "proxy.peer_server.connections",
    "proxy.peer_client.rpc",
    "proxy.peer_client.rpc.count",
    "proxy.peer_client.rpc_duration_seconds.bucket",
    "proxy.peer_client.rpc_duration_seconds.count",
    "proxy.peer_client.rpc_duration_seconds.sum",
    "proxy.peer_client.message_sent_size.bucket",
    "proxy.peer_client.message_sent_size.count",
    "proxy.peer_client.message_sent_size.sum",
    "proxy.peer_client.message_received_size.bucket",
    "proxy.peer_client.message_received_size.count",
    "proxy.peer_client.message_received_size.sum",
    "proxy.peer_server.rpc",
    "proxy.peer_server.rpc_duration_seconds.bucket",
    "proxy.peer_server.rpc_duration_seconds.count",
    "proxy.peer_server.rpc_duration_seconds.sum",
    "proxy.peer_server.message_sent_size.bucket",
    "proxy.peer_server.message_sent_size.count",
    "proxy.peer_server.message_sent_size.sum",
    "proxy.peer_server.message_received_size.bucket",
    "proxy.peer_server.message_received_size.count",
    "proxy.peer_server.message_received_size.sum",
    "proxy.ssh_sessions_total",
    "proxy.missing_ssh_tunnels",
    "proxy.remote_clusters",
    "proxy.teleport_connect_to_node_attempts.count",
    "proxy.teleport_reverse_tunnels_connected",
    "proxy.trusted_clusters",
    "proxy.teleport_proxy_db_connection_setup_time_seconds.bucket",
    "proxy.teleport_proxy_db_connection_setup_time_seconds.count",
    "proxy.teleport_proxy_db_connection_setup_time_seconds.sum",
    "proxy.teleport_proxy_db_connection_dial_attempts.count",
    "proxy.teleport_proxy_db_connection_dial_failures.count",
    "proxy.teleport_proxy_db_attempted_servers_total.bucket",
    "proxy.teleport_proxy_db_attempted_servers_total.count",
    "proxy.teleport_proxy_db_attempted_servers_total.sum",
    "proxy.teleport_proxy_db_connection_tls_config_time_seconds.bucket",
    "proxy.teleport_proxy_db_connection_tls_config_time_seconds.count",
    "proxy.teleport_proxy_db_connection_tls_config_time_seconds.sum",
    "proxy.teleport_proxy_db_active_connections_total",
]


def test_proxy_teleport_metrics(dd_run_check, aggregator, mock_http_response, metrics_path):
    mock_http_response(file_path=metrics_path)

    instance = {"diagnostic_url": "http://hostname:3000"}
    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in PROXY_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
