# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import get_here
from datadog_checks.teleport import TeleportCheck

pytestmark = [pytest.mark.unit]


def test_connect_exception(dd_run_check):
    instance = {}
    check = TeleportCheck('teleport', {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)


COMMON_METRICS = [
    "process.state",
    "certificate_mismatch.count",
    "rx.count",
    "server_interactive_sessions_total",
    "teleport.build_info",
    "teleport.cache_events.count",
    "teleport.cache_stale_events.count",
    "tx.count",
]


def test_common_teleport_metrics(dd_run_check, aggregator, mock_http_response):
    fixtures_path = os.path.join(get_here(), 'fixtures', 'metrics.txt')
    mock_http_response(file_path=fixtures_path)

    instance = {"diagnostic_url": "http://hostname:3000"}
    check = TeleportCheck('teleport', {}, [instance])
    dd_run_check(check)

    for metric in COMMON_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")


PROXY_METRICS = [
    "failed_connect_to_node_attempts.count",
    "failed_login_attempts.count",
    "grpc_client_started.count",
    "grpc_client_handled.count",
    "grpc_client_msg_received.count",
    "grpc_client_msg_sent.count",
    "proxy_connection_limit_exceeded.count",
    # "proxy_peer_client_dial_error.count",
    # "proxy_peer_server_connections",
    # "proxy_peer_client_rpc",
    # "proxy_peer_client_rpc.count",
    # "proxy_peer_client_rpc_duration_seconds",
    # "proxy_peer_client_message_sent_size",
    # "proxy_peer_client_message_received_size",
    # "proxy_peer_server_connections",
    # "proxy_peer_server_rpc",
    # "proxy_peer_server_rpc.count",
    # "proxy_peer_server_rpc_duration_seconds",
    # "proxy_peer_server_message_sent_size",
    # "proxy_peer_server_message_received_size",
    "proxy_ssh_sessions_total",
    "proxy_missing_ssh_tunnels",
    # "remote_clusters",
    "teleport_connect_to_node_attempts.count",
    # "teleport_reverse_tunnels_connected",
    # "trusted_clusters",
    # "teleport_proxy_db_connection_setup_time_seconds",
    # "teleport_proxy_db_connection_dial_attempts.count",
    # "teleport_proxy_db_connection_dial_failures.count",
    # "teleport_proxy_db_attempted_servers_total",
    # "teleport_proxy_db_connection_tls_config_time_seconds",
    # "teleport_proxy_db_active_connections_total",
]


def test_proxy_teleport_metrics(dd_run_check, aggregator, mock_http_response):
    fixtures_path = os.path.join(get_here(), 'fixtures', 'metrics.txt')
    mock_http_response(file_path=fixtures_path)

    instance = {"diagnostic_url": "http://hostname:3000"}
    check = TeleportCheck('teleport', {}, [instance])
    dd_run_check(check)

    for metric in PROXY_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
