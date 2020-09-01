# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()

IOT_EDGE_LIBIOTHSM_STD_URL = os.environ["IOT_EDGE_LIBIOTHSM_STD_URL"]
IOT_EDGE_IOTEDGE_URL = os.environ["IOT_EDGE_IOTEDGE_URL"]
IOT_EDGE_AGENT_IMAGE = os.environ["IOT_EDGE_AGENT_IMAGE"]

# Must be passed explicitly when starting the environment.
# Obtained from: `az iot hub device-identity connection-string show --device-id <DEVICE_ID> --hub-name <HUB_NAME>`
IOT_EDGE_DEVICE_CONNECTION_STRING = os.environ['IOT_EDGE_DEVICE_CONNECTION_STRING']
