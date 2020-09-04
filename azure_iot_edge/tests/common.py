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

CUSTOM_TAGS = ['env:testing']

TAGS = [
    *CUSTOM_TAGS,
    'edge_device:testEdgeDevice',
    'iothub:iot-edge-dev-hub.azure-devices.net',
]

HUB_METRICS = [
    ('azure_iot_edge.edge_hub.queue.length', AggregatorStub.GAUGE),
]  # type: List[Tuple[str, int]]

MODULE_METRICS = [
    ('azure_iot_edge.edge_agent.total_network_out_bytes', AggregatorStub.GAUGE),
]  # type: List[Tuple[str, int]]

MODULES = [
    'edgeHub',
    'edgeAgent',
    'SimulatedTemperatureSensor',
]

E2E_LIBIOTHSM_STD_URL = os.environ['IOT_EDGE_E2E_LIBIOTHSM_STD_URL']
E2E_IOTEDGE_URL = os.environ['IOT_EDGE_E2E_IOTEDGE_URL']
E2E_IMAGE = os.environ['IOT_EDGE_E2E_IMAGE']

# Obtained from: `az iot hub device-identity connection-string show --device-id <DEVICE_ID> --hub-name <HUB_NAME>`
E2E_IOT_EDGE_CONNSTR = os.environ.get('IOT_EDGE_CONNSTR', '')

E2E_NETWORK = 'iot-edge-network'
E2E_EDGE_HUB_PROMETHEUS_URL = 'http://localhost:9601/metrics'
E2E_EDGE_AGENT_PROMETHEUS_URL = 'http://localhost:9602/metrics'
E2E_EXTRA_SPAWNED_CONTAINERS = [
    # Spawned by the Edge Agent after device has started.
    'edgeHub',
    'SimulatedTemperatureSensor',
]

E2E_METRICS = [
    'azure_iot_edge.edge_hub.queue.length',
    'azure_iot_edge.edge_agent.total_network_out_bytes',
]

E2E_TAGS = [
    *CUSTOM_TAGS,
    'edge_device:testEdgeDevice',
    'iothub:iot-edge-dev-hub.azure-devices.net',
]
