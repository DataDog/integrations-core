# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.proxmox.config_models import ConfigMixin

RESOURCE_TYPE_MAP = {
    'qemu': 'vm',
    'lxc': 'container',
    'storage': 'storage',
    'node': 'node',
    'pool': 'pool',
    'sdn': 'sdn',
}

TAG_REMAPPER = {''}


class ProxmoxCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'proxmox'

    def __init__(self, name, init_config, instances):
        super(ProxmoxCheck, self).__init__(name, init_config, instances)
        self.check_initializations.append(self._parse_config)

    def _parse_config(self):
        self.base_tags = [f"proxmox_server:{self.config.proxmox_server}"]
        if self.config.tags:
            self.base_tags.extend(self.config.tags)

    def check(self, _):
        try:
            response = self.http.get(f"{self.config.proxmox_server}/version")
            response.raise_for_status()
            response_json = response.json()
            version = response_json.get("data", {}).get("version")
            self.set_metadata('version', version)
            self.gauge("api.up", 1, tags=self.base_tags)

        except Exception as e:
            self.log.error("Encountered an Exception when hitting the Proxmox API %s", e)
            self.gauge("api.up", 0, tags=self.base_tags)

        resources_response = self.http.get(f"{self.config.proxmox_server}/cluster/resources")
        resources_response_json = resources_response.json()
        resources = resources_response_json.get("data", [])
        for resource in resources:
            resource_type = resource.get('type')
            resource_type_remapped = RESOURCE_TYPE_MAP.get(resource_type, resource_type)
            resource_name = resource.get('name')
            if resource_name is None:
                # some resources don't have a name attribute
                resource_name = resource.get(resource.get('type', ''))

            resource_id = resource.get('id')
            resource_tags = {
                f'proxmox_type:{resource_type_remapped}',
                f'proxmox_{resource_type_remapped}:{resource_name}',
                f'proxmox_id:{resource_id}',
            }
            node = resource.get('node')
            if node:
                resource_tags.add(f'proxmox_node:{node}')

            pool = resource.get('pool')
            if pool:
                resource_tags.add(f'proxmox_pool:{pool}')
            self.gauge(
                f'{resource_type_remapped}.count',
                1,
                tags=self.base_tags + list(resource_tags),
            )
