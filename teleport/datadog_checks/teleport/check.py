# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2

PROXY_METRICS_MAP = {
    "failed_connect_to_node_attempts": "proxy.failed_connect_to_node_attempts",
    "failed_login_attempts": "proxy.failed_login_attempts",
    "grpc_client_started": "proxy.grpc.client.started",
    "grpc_client_handled": "proxy.grpc.client.handled",
    "grpc_client_msg_received": "proxy.grpc.client.msg_received",
    "grpc_client_msg_sent": "proxy.grpc.client.msg_sent",
    "grpc_server_handled": "proxy.grpc.server.handled",
    "grpc_server_msg_received": "proxy.grpc.server.msg_received",
    "grpc_server_msg_sent": "proxy.grpc.server.msg_sent",
    "grpc_server_started": "proxy.grpc.server.started",
    "proxy_connection_limit_exceeded": "proxy.connection_limit_exceeded",
    "proxy_peer_client_dial_error": "proxy.peer_client.dial_error",
    "proxy_peer_server_connections": "proxy.peer_server.connections",
    "proxy_peer_client_rpc": {"name": "proxy.peer_client.rpc", "type": "native_dynamic"},
    "proxy_peer_client_rpc_duration_seconds": "proxy.peer_client.rpc_duration_seconds",
    "proxy_peer_client_message_sent_size": "proxy.peer_client.message_sent_size",
    "proxy_peer_client_message_received_size": "proxy.peer_client.message_received_size",
    "proxy_peer_server_rpc": "proxy.peer_server.rpc",
    "proxy_peer_server_rpc_duration_seconds": "proxy.peer_server.rpc_duration_seconds",
    "proxy_peer_server_message_sent_size": "proxy.peer_server.message_sent_size",
    "proxy_peer_server_message_received_size": "proxy.peer_server.message_received_size",
    "proxy_ssh_sessions_total": "proxy.ssh_sessions_total",
    "proxy_missing_ssh_tunnels": "proxy.missing_ssh_tunnels",
    "remote_clusters": "proxy.remote_clusters",
    "teleport_connect_to_node_attempts": "proxy.teleport_connect_to_node_attempts",
    "teleport_reverse_tunnels_connected": "proxy.teleport_reverse_tunnels_connected",
    "trusted_clusters": "proxy.trusted_clusters",
    "teleport_proxy_db_connection_setup_time_seconds": "proxy.teleport_proxy_db_connection_setup_time_seconds",
    "teleport_proxy_db_connection_dial_attempts": "proxy.teleport_proxy_db_connection_dial_attempts",
    "teleport_proxy_db_connection_dial_failures": "proxy.teleport_proxy_db_connection_dial_failures",
    "teleport_proxy_db_attempted_servers_total": "proxy.teleport_proxy_db_attempted_servers_total",
    "teleport_proxy_db_connection_tls_config_time_seconds": "proxy.teleport_proxy_db_connection_tls_config_time_seconds",
    "teleport_proxy_db_active_connections_total": "proxy.teleport_proxy_db_active_connections_total",
}

COMMON_METRICS_MAP = {
    'process_state': 'process.state',
    'certificate_mismatch': 'certificate_mismatch',
    'rx': 'rx',
    'server_interactive_sessions_total': 'server_interactive_sessions_total',
    'teleport_build_info': 'teleport.build_info',
    'teleport_cache_events': 'teleport.cache_events',
    'teleport_cache_stale_events': 'teleport.cache_stale_events',
    'tx': 'tx',
}

METRIC_MAP = {**COMMON_METRICS_MAP, **PROXY_METRICS_MAP}


class TeleportCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'teleport'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def check(self, _):
        try:
            super().check(_)
            response = self.http.get(self.diagnostic_url + "/healthz")
            response.raise_for_status()
            self.service_check("health.up", self.OK)
        except Exception as e:
            self.service_check("health.up", self.CRITICAL, message=str(e))
        finally:
            pass

    def _parse_config(self):
        self.diagnostic_url = self.instance.get("diagnostic_url")
        if self.diagnostic_url:
            self.instance.setdefault("openmetrics_endpoint", self.diagnostic_url + "/metrics")
            self.instance.setdefault("metrics", [METRIC_MAP])
            self.instance.setdefault("rename_labels", {'version': "teleport_version"})
