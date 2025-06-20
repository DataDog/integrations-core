# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, JSONDecodeError, Timeout

from datadog_checks.base import AgentCheck
from datadog_checks.proxmox.config_models import ConfigMixin

from .constants import NODE_RESOURCE, OK_STATUS, RESOURCE_METRICS, RESOURCE_TYPE_MAP, VM_RESOURCE


class ProxmoxCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'proxmox'

    def __init__(self, name, init_config, instances):
        super(ProxmoxCheck, self).__init__(name, init_config, instances)
        self.check_initializations.append(self._parse_config)

    def _parse_config(self):
        self.base_tags = [f"proxmox_server:{self.config.proxmox_server}"]
        if self.config.tags:
            self.base_tags.extend(self.config.tags)

    def _submit_resource_metrics(self, resource, resource_type, tags, hostname):
        for metric_name in RESOURCE_METRICS:
            metric_value = resource.get(metric_name)
            if metric_value is not None:
                self.gauge(f'{resource_type}.{metric_name}', metric_value, tags=tags, hostname=hostname)

    def check(self, _):
        try:
            response = self.http.get(f"{self.config.proxmox_server}/version")
            response.raise_for_status()
            response_json = response.json()
            version = response_json.get("data", {}).get("version")
            self.set_metadata('version', version)
            self.gauge("api.up", 1, tags=self.base_tags)

        except (HTTPError, InvalidURL, ConnectionError, Timeout) as e:
            self.log.error(
                "Encountered an Exception when hitting the Proxmox API %s: %s", self.config.proxmox_server, e
            )
            self.gauge("api.up", 0, tags=self.base_tags)
            return

        resources_response = self.http.get(f"{self.config.proxmox_server}/cluster/resources")
        resources_response_json = resources_response.json()
        resources = resources_response_json.get("data", [])

        external_tags = []

        for resource in resources:
            resource_type = resource.get('type')
            node = resource.get('node')
            resource_type_remapped = RESOURCE_TYPE_MAP.get(resource_type, resource_type)
            resource_id = resource.get('id')
            resource_name = resource.get('name')
            if resource_name is None:
                # some resource types don't have a name attribute
                resource_name = resource.get(resource.get('type', ''))

            hostname = None
            if resource_type_remapped == VM_RESOURCE:
                vmid = resource.get('vmid')
                try:
                    url = f"{self.config.proxmox_server}/nodes/{node}/qemu/{vmid}/agent/get-host-name"
                    hostname_response = self.http.get(url)
                    hostname_json = hostname_response.json()
                except (HTTPError, InvalidURL, ConnectionError, Timeout, JSONDecodeError) as e:
                    self.log.info(
                        "Failed to get hostname for vm %s on node %s; endpoint: %s; %s",
                        vmid,
                        node,
                        self.config.proxmox_server,
                        e,
                    )
                    hostname_json = {}
                hostname = hostname_json.get("data", {}).get("result", {}).get("host-name", resource_name)
            elif resource_type_remapped == NODE_RESOURCE:
                hostname = node

            resource_tags = {
                f'proxmox_type:{resource_type_remapped}',
                f'proxmox_{resource_type_remapped}:{resource_name}',
                f'proxmox_id:{resource_id}',
            }

            proxmox_tags = resource.get('tags')
            if proxmox_tags:
                proxmox_tags = proxmox_tags.split(';')
                resource_tags.update(proxmox_tags)

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

            status = resource.get("status")
            if status is None:
                # pools don't have a status attribute
                continue

            status = 1 if status in OK_STATUS else 0
            tags = []
            if not hostname:
                tags = self.base_tags + list(resource_tags)
            elif status == 1:
                external_tags.append((hostname, {self.__NAMESPACE__: self.base_tags + list(resource_tags)}))
            else:
                # don't collect data about vms and nodes that are powered off
                continue

            self.gauge(
                f'{resource_type_remapped}.up',
                status,
                tags,
                hostname=hostname,
            )
            self._submit_resource_metrics(resource, resource_type_remapped, tags, hostname)

        self.set_external_tags(external_tags)
