# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import get_here

HERE = get_here()

# Obtained from: `az iot hub device-identity connection-string show --device-id <DEVICE_ID> --hub-name <HUB_NAME>`
IOT_DEVICE_CONNECTION_STRING = 'TODO_IS_THIS_SENSITIVE_DATA?'  # noqa: E501

# IOT_CONTAINER_IP = '172.17.0.2'
IOT_PROMETHEUS_PORT = 9600
