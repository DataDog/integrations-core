# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import copy
from typing import Any  # noqa: F401
from urllib.parse import urljoin

import requests

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2
from datadog_checks.traefik_mesh.config_models import ConfigMixin
from datadog_checks.traefik_mesh.metrics import METRIC_MAP, RENAME_LABELS

PROXY_VERSION = '/api/version'
MESH_READY_STATUS = '/api/status/nodes'
CONTROLLER_READINESS = '/api/status/readiness'


class TraefikMeshCheck(OpenMetricsBaseCheckV2, ConfigMixin):

    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'traefik_mesh'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self.traefik_controller_api_endpoint = self.instance.get('traefik_controller_api_endpoint')
        self.traefik_proxy_api_endpoint = self.instance.get('traefik_proxy_api_endpoint')
        self.tags = self.instance.get('tags', [])
        self.tags = self.tags + [f'controller_endpoint:{self.traefik_controller_api_endpoint}']

    def get_default_config(self):
        return {
            "metrics": [METRIC_MAP],
            "rename_labels": RENAME_LABELS,
        }

    def check(self, _):
        try:
            super().check(_)

        finally:
            if self.traefik_controller_api_endpoint:
                self.submit_controller_readiness_service_check()
                traefik_node_status = self.get_mesh_ready_status()
                self.submit_mesh_ready_status(traefik_node_status)

            self._submit_version()

    def submit_controller_readiness_service_check(self):
        """Submits Traefik Controller readiness status from the Traefik Controller"""

        controller_status_url = urljoin(self.traefik_controller_api_endpoint, CONTROLLER_READINESS)
        response = self.http.get(controller_status_url)
        self.service_check('controller.ready', AgentCheck.OK if response.ok else AgentCheck.CRITICAL, tags=self.tags)

    def submit_mesh_ready_status(self, nodes):
        """Submits Traefik Mesh readiness status from the Traefik Controller"""

        if not nodes:
            return

        for node in nodes:
            node_tags = copy(self.tags)
            node_name = node.get('Name')
            node_ip = node.get('IP')
            status = node.get('Ready')
            # Set the node name and IP as tags
            node_tags.append(f'node_name:{node_name}')
            node_tags.append(f'node_ip:{node_ip}')

            self.log.debug("Node %s Ready: %s", node_name, status)
            self.gauge('node.ready', 1 if status == 'true' else 0, tags=node_tags)

    def get_mesh_ready_status(self):
        """Fetches Traefik Mesh node status from the Controller"""

        node_status_url = urljoin(self.traefik_controller_api_endpoint, MESH_READY_STATUS)
        node_status = self._get_json(node_status_url)
        if not node_status:
            self.log.warning("Unable to fetch Traefik Mesh node status")
            return None

        self.log.info("Node status: %s", node_status)

        return node_status

    def get_version(self, url):
        """Fetches Traefik Proxy version from the Proxy API"""

        version_url = urljoin(self.traefik_proxy_api_endpoint, PROXY_VERSION)
        response = self._get_json(version_url)
        if not response:
            self.log.warning("Unable to fetch Traefik Proxy version")
            return None

        version = response.get('Version')
        return version

    @AgentCheck.metadata_entrypoint
    def _submit_version(self):
        """Submit the version metadata for the Traefik Proxy instance"""

        try:
            if version := self.get_version():
                self.log.debug("Set version %s for Traefik Proxy", version)
                self.set_metadata("version", version)
        except Exception as e:
            self.log.debug("Could not determine Traefik Proxy version: %s", str(e))

    def _get_json(self, url):
        try:
            resp = self.http.get(url)
            resp.raise_for_status()
            return resp.json()
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
            self.warning(
                "Couldn't connect to URL: %s with exception: %s. Please verify the address is reachable", url, e
            )
        except requests.exceptions.Timeout as e:
            self.warning("Connection timeout when connecting to %s: %s", url, e)
        return None
