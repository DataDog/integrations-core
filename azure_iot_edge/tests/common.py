# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import List, Tuple

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev import get_here

HERE = get_here()

MOCK_SERVER_PORT = 9678
MOCK_EDGE_HUB_PROMETHEUS_URL = 'http://localhost:{}/metrics/edge_hub.txt'.format(MOCK_SERVER_PORT)
MOCK_EDGE_AGENT_PROMETHEUS_URL = 'http://localhost:{}/metrics/edge_agent.txt'.format(MOCK_SERVER_PORT)
MOCK_SECURITY_DAEMON_MANAGEMENT_API_URL = 'http://localhost:{}/mgmt.json'.format(MOCK_SERVER_PORT)

CUSTOM_TAGS = ['env:testing']

TAGS = CUSTOM_TAGS + [
    'edge_device:testEdgeDevice',
    'iothub:iot-edge-dev-hub.azure-devices.net',
]

HUB_METRICS = [
    ('azure_iot_edge.edge_hub.gettwin_total', AggregatorStub.MONOTONIC_COUNT),
    ('azure_iot_edge.edge_hub.messages_received_total', AggregatorStub.MONOTONIC_COUNT),
    ('azure_iot_edge.edge_hub.messages_sent_total', AggregatorStub.MONOTONIC_COUNT),
    ('azure_iot_edge.edge_hub.reported_properties_total', AggregatorStub.MONOTONIC_COUNT),
    ('azure_iot_edge.edge_hub.gettwin_duration_seconds.sum', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.gettwin_duration_seconds.count', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.gettwin_duration_seconds.quantile', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.message_send_duration_seconds.sum', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.message_send_duration_seconds.count', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.message_send_duration_seconds.quantile', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.message_process_duration_seconds.sum', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.message_process_duration_seconds.count', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.message_process_duration_seconds.quantile', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.reported_properties_update_duration_seconds.sum', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.reported_properties_update_duration_seconds.count', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.reported_properties_update_duration_seconds.quantile', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.direct_method_duration_seconds.sum', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.direct_method_duration_seconds.count', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.direct_method_duration_seconds.quantile', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.direct_methods_total', AggregatorStub.MONOTONIC_COUNT),
    ('azure_iot_edge.edge_hub.queue_length', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.messages_dropped_total', AggregatorStub.MONOTONIC_COUNT),
    ('azure_iot_edge.edge_hub.messages_unack_total', AggregatorStub.MONOTONIC_COUNT),
    ('azure_iot_edge.edge_hub.offline_count_total', AggregatorStub.MONOTONIC_COUNT),
    ('azure_iot_edge.edge_hub.offline_duration_seconds.sum', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.offline_duration_seconds.count', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.offline_duration_seconds.quantile', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_hub.operation_retry_total', AggregatorStub.MONOTONIC_COUNT),
    ('azure_iot_edge.edge_hub.client_connect_failed_total', AggregatorStub.MONOTONIC_COUNT),
]  # type: List[Tuple[str, int]]

AGENT_METRICS = [
    (
        'azure_iot_edge.edge_agent.iotedged_uptime_seconds',
        AggregatorStub.GAUGE,
        [],
    ),
    (
        'azure_iot_edge.edge_agent.unsuccessful_iothub_syncs_total',
        AggregatorStub.MONOTONIC_COUNT,
        [],
    ),
    (
        'azure_iot_edge.edge_agent.iothub_syncs_total',
        AggregatorStub.MONOTONIC_COUNT,
        [],
    ),
    (
        'azure_iot_edge.edge_agent.host_uptime_seconds',
        AggregatorStub.GAUGE,
        [],
    ),
    (
        'azure_iot_edge.edge_agent.deployment_time_seconds.sum',
        AggregatorStub.GAUGE,
        [],
    ),
    (
        'azure_iot_edge.edge_agent.deployment_time_seconds.count',
        AggregatorStub.GAUGE,
        [],
    ),
    (
        'azure_iot_edge.edge_agent.deployment_time_seconds.quantile',
        AggregatorStub.GAUGE,
        ['quantile:0.5'],
    ),
    (
        'azure_iot_edge.edge_agent.deployment_time_seconds.quantile',
        AggregatorStub.GAUGE,
        ['quantile:0.9'],
    ),
    (
        'azure_iot_edge.edge_agent.deployment_time_seconds.quantile',
        AggregatorStub.GAUGE,
        ['quantile:0.95'],
    ),
    (
        'azure_iot_edge.edge_agent.deployment_time_seconds.quantile',
        AggregatorStub.GAUGE,
        ['quantile:0.99'],
    ),
    (
        'azure_iot_edge.edge_agent.deployment_time_seconds.quantile',
        AggregatorStub.GAUGE,
        ['quantile:0.999'],
    ),
    (
        'azure_iot_edge.edge_agent.deployment_time_seconds.quantile',
        AggregatorStub.GAUGE,
        ['quantile:0.9999'],
    ),
    (
        'azure_iot_edge.edge_agent.used_cpu_percent.sum',
        AggregatorStub.GAUGE,
        ['module_name:host'],
    ),
    (
        'azure_iot_edge.edge_agent.used_cpu_percent.count',
        AggregatorStub.GAUGE,
        ['module_name:host'],
    ),
    (
        'azure_iot_edge.edge_agent.used_cpu_percent.quantile',
        AggregatorStub.GAUGE,
        ['module_name:host', 'quantile:0.5'],
    ),
    (
        'azure_iot_edge.edge_agent.used_cpu_percent.quantile',
        AggregatorStub.GAUGE,
        ['module_name:host', 'quantile:0.9'],
    ),
    (
        'azure_iot_edge.edge_agent.used_cpu_percent.quantile',
        AggregatorStub.GAUGE,
        ['module_name:host', 'quantile:0.95'],
    ),
    (
        'azure_iot_edge.edge_agent.used_cpu_percent.quantile',
        AggregatorStub.GAUGE,
        ['module_name:host', 'quantile:0.99'],
    ),
    (
        'azure_iot_edge.edge_agent.used_cpu_percent.quantile',
        AggregatorStub.GAUGE,
        ['module_name:host', 'quantile:0.999'],
    ),
    (
        'azure_iot_edge.edge_agent.used_cpu_percent.quantile',
        AggregatorStub.GAUGE,
        ['module_name:host', 'quantile:0.9999'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.sum',
        AggregatorStub.GAUGE,
        ['command:wrap'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.count',
        AggregatorStub.GAUGE,
        ['command:wrap'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:wrap', 'quantile:0.5'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:wrap', 'quantile:0.9'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:wrap', 'quantile:0.95'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:wrap', 'quantile:0.99'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:wrap', 'quantile:0.999'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:wrap', 'quantile:0.9999'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.sum',
        AggregatorStub.GAUGE,
        ['command:create'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.count',
        AggregatorStub.GAUGE,
        ['command:create'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:create', 'quantile:0.5'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:create', 'quantile:0.9'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:create', 'quantile:0.95'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:create', 'quantile:0.99'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:create', 'quantile:0.999'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:create', 'quantile:0.9999'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.sum',
        AggregatorStub.GAUGE,
        ['command:start'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.count',
        AggregatorStub.GAUGE,
        ['command:start'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:start', 'quantile:0.5'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:start', 'quantile:0.9'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:start', 'quantile:0.95'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:start', 'quantile:0.99'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:start', 'quantile:0.999'],
    ),
    (
        'azure_iot_edge.edge_agent.command_latency_seconds.quantile',
        AggregatorStub.GAUGE,
        ['command:start', 'quantile:0.9999'],
    ),
    (
        'azure_iot_edge.edge_agent.module_start_total',
        AggregatorStub.MONOTONIC_COUNT,
        ['module_name:edgeHub', 'module_version:'],
    ),
    (
        'azure_iot_edge.edge_agent.module_start_total',
        AggregatorStub.MONOTONIC_COUNT,
        ['module_name:SimulatedTemperatureSensor', 'module_version:1.0'],
    ),
    (
        'azure_iot_edge.edge_agent.module_stop_total',
        AggregatorStub.MONOTONIC_COUNT,
        ['module_name:edgeHub', 'module_version:'],
    ),
    (
        'azure_iot_edge.edge_agent.module_stop_total',
        AggregatorStub.MONOTONIC_COUNT,
        ['module_name:SimulatedTemperatureSensor', 'module_version:1.0'],
    ),
]  # type: List[Tuple[str, int, List[str]]]

MODULES = [
    'edgeHub',
    'edgeAgent',
    'SimulatedTemperatureSensor',
]

MODULE_METRICS = [
    (
        'azure_iot_edge.edge_agent.total_network_in_bytes',
        AggregatorStub.GAUGE,
    ),
    ('azure_iot_edge.edge_agent.total_network_out_bytes', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_agent.total_disk_read_bytes', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_agent.total_disk_write_bytes', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_agent.total_disk_space_bytes', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_agent.created_pids_total', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_agent.total_time_expected_running_seconds', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_agent.total_time_running_correctly_seconds', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_agent.used_memory_bytes', AggregatorStub.GAUGE),
    ('azure_iot_edge.edge_agent.total_memory_bytes', AggregatorStub.GAUGE),
]  # type: List[Tuple[str, int]]

E2E_LIBIOTHSM_STD_URL = os.environ['IOT_EDGE_E2E_LIBIOTHSM_STD_URL']
E2E_IOTEDGE_URL = os.environ['IOT_EDGE_E2E_IOTEDGE_URL']
E2E_IMAGE = os.environ['IOT_EDGE_E2E_IMAGE']

# Obtained from: `az iot hub device-identity connection-string show --device-id <DEVICE_ID> --hub-name <HUB_NAME>`
E2E_IOT_EDGE_CONNSTR = os.environ.get('IOT_EDGE_CONNSTR', '')

E2E_NETWORK = 'iot-edge-network'
E2E_EDGE_HUB_PROMETHEUS_URL = 'http://localhost:9601/metrics'
E2E_EDGE_AGENT_PROMETHEUS_URL = 'http://localhost:9602/metrics'
E2E_SECURITY_DAEMON_MANAGEMENT_API_URL = 'http://localhost:15580/'
E2E_EXTRA_SPAWNED_CONTAINERS = [
    # Spawned by the Edge Agent after device has started.
    'edgeHub',
    'SimulatedTemperatureSensor',
]

E2E_METRICS = (
    # All metrics...
    {name for name, _ in MODULE_METRICS}
    .union(name for name, _, _ in AGENT_METRICS)
    .union(name for name, _ in HUB_METRICS)
    # ... Except a few that don't get emitted by default.
    .difference(
        {
            'azure_iot_edge.edge_agent.module_stop_total',
            'azure_iot_edge.edge_agent.unsuccessful_iothub_syncs_total',
            'azure_iot_edge.edge_agent.total_disk_space_bytes',
            'azure_iot_edge.edge_hub.direct_methods_total',
            'azure_iot_edge.edge_hub.direct_method_duration_seconds.sum',
            'azure_iot_edge.edge_hub.direct_method_duration_seconds.count',
            'azure_iot_edge.edge_hub.direct_method_duration_seconds.quantile',
            'azure_iot_edge.edge_hub.messages_unack_total',
            'azure_iot_edge.edge_hub.messages_dropped_total',
            'azure_iot_edge.edge_hub.offline_count_total',
            'azure_iot_edge.edge_hub.operation_retry_total',
            'azure_iot_edge.edge_hub.client_connect_failed_total',
        }
    )
)

E2E_TAGS = CUSTOM_TAGS + [
    'edge_device:testEdgeDevice',
    'iothub:iot-edge-dev-hub.azure-devices.net',
]

E2E_METADATA = {
    'env_vars': {
        'DD_LOGS_ENABLED': 'true',
    },
    'docker_volumes': [
        '/var/run/docker.sock:/var/run/docker.sock',
    ],
    'start_commands': [
        # Ensure the Agent has access to the autodiscovery config template.
        'cp -r /home/azure_iot_edge/datadog_checks/azure_iot_edge/data/auto_conf.yaml /etc/datadog-agent/conf.d/azure_iot_edge.d/auto_conf.yaml',  # noqa: E501
    ],
}
