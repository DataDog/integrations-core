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

# Each component has its own namespace
CONTROLLER_NAMESPACE = 'pinot.controller'
SERVER_NAMESPACE = 'pinot.server'
BROKER_NAMESPACE = 'pinot.broker'
MINION_NAMESPACE = 'pinot.minion'

# Sample metrics to check for each component (unit tests)
# Using gauge metrics that are guaranteed to be present in fixtures
# The namespace (e.g., pinot.controller) is the prefix, followed by the metric name
CONTROLLER_METRICS = [
    'pinot.controller.jvm_memory_bytes_used',
    'pinot.controller.jvm_threads_current',
    'pinot.controller.process_open_fds',
]

SERVER_METRICS = [
    'pinot.server.jvm_memory_bytes_used',
    'pinot.server.jvm_threads_current',
    'pinot.server.process_open_fds',
]

BROKER_METRICS = [
    'pinot.broker.jvm_memory_bytes_used',
    'pinot.broker.jvm_threads_current',
    'pinot.broker.process_open_fds',
]

MINION_METRICS = [
    'pinot.minion.jvm_memory_bytes_used',
    'pinot.minion.jvm_threads_current',
    'pinot.minion.process_open_fds',
]
