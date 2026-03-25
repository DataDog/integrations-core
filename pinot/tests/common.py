# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()

# Individual component ports (used for unit tests with mocked responses)
CONTROLLER_PORT = 8009
SERVER_PORT = 8008
BROKER_PORT = 8007
MINION_PORT = 8006


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


# Unit test instances (use separate ports for mocking)
CONTROLLER_INSTANCE = {
    'controller_endpoint': f'http://{HOST}:{CONTROLLER_PORT}/metrics',
    'tags': ['test:test'],
}

SERVER_INSTANCE = {
    'server_endpoint': f'http://{HOST}:{SERVER_PORT}/metrics',
    'tags': ['test:test'],
}

BROKER_INSTANCE = {
    'broker_endpoint': f'http://{HOST}:{BROKER_PORT}/metrics',
    'tags': ['test:test'],
}

MINION_INSTANCE = {
    'minion_endpoint': f'http://{HOST}:{MINION_PORT}/metrics',
    'tags': ['test:test'],
}

CONTROLLER_NAMESPACE = 'pinot.controller'
SERVER_NAMESPACE = 'pinot.server'
BROKER_NAMESPACE = 'pinot.broker'
MINION_NAMESPACE = 'pinot.minion'

CONTROLLER_METRICS = [
    'pinot.controller.can_connect',
    'pinot.controller.jvm_buffer_pool_capacity_bytes',
    'pinot.controller.jvm_buffer_pool_used_bytes',
    'pinot.controller.jvm_gc_collection_seconds.count',
    'pinot.controller.jvm_gc_collection_seconds.sum',
    'pinot.controller.jvm_memory_bytes_max',
    'pinot.controller.jvm_memory_bytes_used',
    'pinot.controller.jvm_threads_current',
    'pinot.controller.pinot_controller_helix_connected_Value',
    'pinot.controller.pinot_controller_offlineTableCount_Value',
    'pinot.controller.pinot_controller_realtimeTableCount_Value',
    'pinot.controller.process_open_fds',
    'pinot.controller.process_cpu_seconds.count',
]

SERVER_METRICS = [
    'pinot.server.can_connect',
    'pinot.server.jvm_memory_bytes_used',
    'pinot.server.jvm_threads_current',
    'pinot.server.pinot_server_helix_connected_Value',
    'pinot.server.pinot_server_queries_Count',
    'pinot.server.process_open_fds',
    'pinot.server.process_cpu_seconds.count',
]

BROKER_METRICS = [
    'pinot.broker.can_connect',
    'pinot.broker.jvm_memory_bytes_used',
    'pinot.broker.jvm_threads_current',
    'pinot.broker.pinot_broker_helix_connected_Value',
    'pinot.broker.pinot_broker_queriesKilled_Count',
    'pinot.broker.process_open_fds',
    'pinot.broker.process_cpu_seconds.count',
]

MINION_METRICS = [
    'pinot.minion.can_connect',
    'pinot.minion.jvm_memory_bytes_used',
    'pinot.minion.jvm_threads_current',
    'pinot.minion.pinot_minion_connected_Value',
    'pinot.minion.pinot_minion_numberOfTasks_Value',
    'pinot.minion.process_open_fds',
    'pinot.minion.process_cpu_seconds.count',
]
