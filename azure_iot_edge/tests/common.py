# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import List, Tuple

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
EDGE_HUB_PROMETHEUS_ENDPOINT = 'http://localhost:9601/metrics'
EDGE_AGENT_PROMETHEUS_ENDPOINT = 'http://localhost:9602/metrics'
EDGE_AGENT_SPAWNED_CONTAINERS = [
    # Spawned by the Edge Agent after device has started.
    'edgeHub',
    'SimulatedTemperatureSensor',
]

TAGS = ['env:testing']

METRICS = [
    ('edge_hub.queue.length', 'gauge'),
    ('edge_agent.total_network_out_bytes', 'gauge'),
]  # type: List[Tuple[str, str]]
