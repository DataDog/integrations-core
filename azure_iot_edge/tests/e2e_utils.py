# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

import requests

from datadog_checks.dev.docker import ComposeFileDown, ComposeFileUp
from datadog_checks.dev.structures import LazyFunction
from datadog_checks.dev.subprocess import run_command

from . import common


class IoTEdgeUp(LazyFunction):
    def __init__(self, compose_file, network_name):
        # type: (str, str) -> None
        self._compose_file_up = ComposeFileUp(compose_file)
        self._network_name = network_name

    def __call__(self):
        # type: () -> Any
        result = run_command(['docker', 'network', 'inspect', self._network_name], capture=True)
        network_exists = result.code == 0
        if not network_exists:
            run_command(['docker', 'network', 'create', self._network_name], check=True)

        return self._compose_file_up()


class IoTEdgeDown(LazyFunction):
    def __init__(self, compose_file, stop_extra_containers):
        # type: (str, list) -> None
        self._compose_file_down = ComposeFileDown(compose_file)
        self._stop_extra_containers = stop_extra_containers

    def __call__(self):
        # type: () -> Any
        run_command(['docker', 'stop'] + self._stop_extra_containers, check=True)
        return self._compose_file_down()


def edge_hub_endpoint_ready():
    # type: () -> bool
    try:
        response = requests.get(common.E2E_EDGE_HUB_PROMETHEUS_URL)
        response.raise_for_status()
    except requests.HTTPError:
        return False
    else:
        return response.status_code == 200


def edge_agent_endpoint_ready():
    # type: () -> bool
    try:
        response = requests.get(common.E2E_EDGE_AGENT_PROMETHEUS_URL)
        response.raise_for_status()
    except requests.HTTPError:
        return False
    else:
        return response.status_code == 200
