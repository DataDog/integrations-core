# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import copy
from typing import Any  # noqa: F401

from six import PY2

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2, is_affirmative
from datadog_checks.traefik_mesh.config_models import ConfigMixin
from datadog_checks.traefik_mesh.metrics import METRIC_MAP, RENAME_LABELS


class TraefikMeshCheck(OpenMetricsBaseCheckV2, ConfigMixin):

    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'traefik_mesh'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self.traefik_proxy_api_endpoint = f"{self.instance.get('openmetrics_endpoint')}/api"
        self.traefik_controller_api_endpoint = self.instance.get('traefik_controller_api_endpoint')
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
                statuses = self.controller_get_node_status(self.traefik_controller_api_endpoint)
                self.node_ready_status(statuses, self.tags)

            self._submit_version()

    def submit_mesh_ready_status(self, node_status, tags):
        """Submits Traefik Mesh readiness status from the Traefik Controller"""

        if not node_status:
            return

        for node in node_status:
            node_tags = copy(tags)
            node_name = node.get('Name')
            status = node.get('Ready')

            node_tags.append(f'node:{node_name}')
            self.log.debug('Node %s Ready: %s', node_name, status)
            self.gauge('node.ready', 1 if status == 'true' else 0, tags=node_tags)

    def get_mesh_ready_status(self, url):
        """Fetches Traefik Mesh node status from the Controller"""

        node_status_url = f'{url}/api/status/nodes'
        try:
            response = self.http.get(node_status_url)
            response.raise_for_status()
            response = response.json()
        except Exception as e:
            self.log.warning('Unable to fetch Traefik Mesh node status: %s', e)
        else:
            node_status = response
            self.log.info('Node status: %s', node_status)

        return node_status

    def get_version(self, url):
        """Fetches Traefik Proxy version from the Proxy API"""

        version_url = f'{url}/version'
        try:
            response = self.http.get(version_url)
            response.raise_for_status()
            response = response.json()
        except Exception as e:
            self.log.warning('Unable to fetch Traefik Proxy version: %s', e)
        else:
            version = response.get('Version')

        return version

    @AgentCheck.metadata_entrypoint
    def _submit_version(self):
        """Submit the version metadata for the Traefik Proxy instance"""

        try:
            if version := self.get_version(self.traefik_proxy_api_endpoint):
                self.log.debug("Set version %s for Traefik Proxy", version)
                self.set_metadata("version", version)
        except Exception as e:
            self.log.debug("Could not determine Traefik Proxy version: %s", str(e))
