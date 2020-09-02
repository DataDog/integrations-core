# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import List, Tuple

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev import get_here

HERE = get_here()

IOT_EDGE_LIBIOTHSM_STD_URL = os.environ["IOT_EDGE_LIBIOTHSM_STD_URL"]
IOT_EDGE_IOTEDGE_URL = os.environ["IOT_EDGE_IOTEDGE_URL"]
IOT_EDGE_AGENT_IMAGE = os.environ["IOT_EDGE_AGENT_IMAGE"]

# Must be passed explicitly when starting the environment.
# Obtained from: `az iot hub device-identity connection-string show --device-id <DEVICE_ID> --hub-name <HUB_NAME>`
IOT_EDGE_DEVICE_CONNECTION_STRING = os.getenv('IOT_EDGE_DEVICE_CONNECTION_STRING')
if not IOT_EDGE_DEVICE_CONNECTION_STRING:
    raise RuntimeError(
        'IOT_EDGE_DEVICE_CONNECTION_STRING is not set or it is empty. '
        'You must pass it explicitly, for example: `IOT_EDGE_DEVICE_CONNECTION_STRING ddev test ...`'
    )

IOT_EDGE_NETWORK = 'iot-edge-network'
EDGE_HUB_PROMETHEUS_URL = 'http://localhost:9601/metrics'
EDGE_AGENT_PROMETHEUS_URL = 'http://localhost:9602/metrics'
EDGE_AGENT_SPAWNED_CONTAINERS = [
    # Spawned by the Edge Agent after device has started.
    'edgeHub',
    'SimulatedTemperatureSensor',
]

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
