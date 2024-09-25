# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 5556


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:{PORT}/metrics",
    "tags": ['test:test', 'integration:appgate_sdp'],
}

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

METRICS_MOCK = [
    'appgate_sdp.appliance.cpu.percent_usage',
    'appgate_sdp.appliance.disk',
    'appgate_sdp.controller.client.authentication.count',
    'appgate_sdp.appliance.active_connections',
    'appgate_sdp.appliance.active_connections.max',
    'appgate_sdp.appliance.audit_events.count',
    'appgate_sdp.appliance.audit_logs.count',
    'appgate_sdp.appliance.certificate_days.remaining',
    'appgate_sdp.appliance.disk.partition_statistic',
    'appgate_sdp.appliance.dns.cache_entries',
    'appgate_sdp.appliance.function.sessions',
    'appgate_sdp.appliance.function.status',
    'appgate_sdp.appliance.function.suspended',
    'appgate_sdp.appliance.image.size',
    'appgate_sdp.appliance.memory',
    'appgate_sdp.appliance.network_interface.speed',
    'appgate_sdp.appliance.network_interface.statistic.count',
    'appgate_sdp.appliance.proxy.protocol_messages.count',
    'appgate_sdp.appliance.snat',
    'appgate_sdp.appliance.spa.dropped_packets.count',
    'appgate_sdp.appliance.spa.packet_authorization_time',
    'appgate_sdp.appliance.spa.packets.count',
    'appgate_sdp.appliance.spa.replay_attack_cache_entries.count',
    'appgate_sdp.appliance.state_size',
    'appgate_sdp.appliance.status',
    'appgate_sdp.appliance.volume_number',
    'appgate_sdp.controller.admin.authentication.count',
    'appgate_sdp.controller.admin.authorization.count',
    'appgate_sdp.controller.admin.evaluate_all_policies.count',
    'appgate_sdp.controller.admin.mfa.count',
    'appgate_sdp.controller.client.authorization.count',
    'appgate_sdp.controller.client.csr.count',
    'appgate_sdp.controller.client.enter.password.count',
    'appgate_sdp.controller.client.evaluate_all_policies.count',
    'appgate_sdp.controller.client.mfa.count',
    'appgate_sdp.controller.client.new_ip_allocation.count',
    'appgate_sdp.controller.client.risk_engine_response.count',
    'appgate_sdp.controller.client.sign_in_with_mfa.count',
    'appgate_sdp.controller.database.conflicts',
    'appgate_sdp.controller.database.node_state',
    'appgate_sdp.controller.database.raft_state',
    'appgate_sdp.controller.database.replication',
    'appgate_sdp.controller.database.replication.slot_replay_lag',
    'appgate_sdp.controller.database.size',
    'appgate_sdp.controller.evaluate_user_claim_script.count',
    'appgate_sdp.controller.ip_pool',
    'appgate_sdp.controller.license',
    'appgate_sdp.controller.license.days_remaining',
    'appgate_sdp.controller.memory_heap',
    'appgate_sdp.controller.policy_evaluator',
    'appgate_sdp.controller.threads',
    'appgate_sdp.gateway.azure_resolver.cache_ttl',
    'appgate_sdp.gateway.dns_forwarder.cache.count',
    'appgate_sdp.gateway.dns_forwarder.domain.count',
    'appgate_sdp.gateway.dns_forwarder.query.count',
    'appgate_sdp.gateway.event_queue.period_peak',
    'appgate_sdp.gateway.event_queue.size',
    'appgate_sdp.gateway.ha_interface.count',
    'appgate_sdp.gateway.http.action.count',
    'appgate_sdp.gateway.http.connection.count',
    'appgate_sdp.gateway.http.open_connection',
    'appgate_sdp.gateway.http.requests.count',
    'appgate_sdp.gateway.illumio.resolver.label',
    'appgate_sdp.gateway.illumio.resolver.cache_ttl',
    'appgate_sdp.gateway.name.resolver.names_missing_resolver',
    'appgate_sdp.gateway.name.resolver.value',
    'appgate_sdp.gateway.policy.evaluator',
    'appgate_sdp.gateway.session.dropped_signin.count',
    'appgate_sdp.gateway.session.event_timing',
    'appgate_sdp.gateway.session.js_exectime',
    'appgate_sdp.gateway.sessiond.heap',
    'appgate_sdp.gateway.sessiond.thread_count',
    'appgate_sdp.gateway.token_size',
    'appgate_sdp.gateway.vpn.client_metric',
    'appgate_sdp.gateway.vpn.memory_usage',
    'appgate_sdp.gateway.vpn.resolved_actions',
    'appgate_sdp.gateway.vpn.rules',
    'appgate_sdp.gateway.vpn.rules_size',
    'appgate_sdp.gateway.vpn.sessions',
    'appgate_sdp.portal.client',
]

# METRICS_MOCK = [f'appgate_sdp.{m}' for m in METRICS_MOCK]
