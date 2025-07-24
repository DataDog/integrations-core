# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, JSONDecodeError, Timeout

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.time import get_current_datetime, get_timestamp
from datadog_checks.proxmox.config_models import ConfigMixin

from .constants import (
    EVENT_TYPE_TO_TITLE,
    NODE_RESOURCE,
    OK_STATUS,
    PERF_METRIC_NAME,
    RESOURCE_COUNT_METRICS,
    RESOURCE_METRIC_NAME,
    RESOURCE_TYPE_MAP,
    VM_RESOURCE,
    resource_type_for_event_type,
)


class ProxmoxCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'proxmox'

    def __init__(self, name, init_config, instances):
        super(ProxmoxCheck, self).__init__(name, init_config, instances)
        self.all_resources = {}
        self.last_event_collect_time = get_current_datetime()
        self.check_initializations.append(self._parse_config)

    def _parse_config(self):
        self.base_tags = [f"proxmox_server:{self.config.proxmox_server}"]
        if self.config.tags:
            self.base_tags.extend(self.config.tags)

    def _submit_resource_metrics(self, resource, tags, hostname):
        for metric_name, metric_name_remapped in RESOURCE_METRIC_NAME.items():
            metric_value = resource.get(metric_name)
            metric_method = self.count if metric_name in RESOURCE_COUNT_METRICS else self.gauge
            if metric_value is not None:
                metric_method(f'{metric_name_remapped}', metric_value, tags=tags, hostname=hostname)

    def _get_vm_hostname(self, vm_id, vm_name, node):
        try:
            url = f"{self.config.proxmox_server}/nodes/{node}/qemu/{vm_id}/agent/get-host-name"
            hostname_response = self.http.get(url)
            hostname_json = hostname_response.json()
        except (HTTPError, InvalidURL, ConnectionError, Timeout, JSONDecodeError) as e:
            self.log.info(
                "Failed to get hostname for vm %s on node %s; endpoint: %s; %s",
                vm_id,
                node,
                self.config.proxmox_server,
                e,
            )
            hostname_json = {}
        hostname = hostname_json.get("data", {}).get("result", {}).get("host-name", vm_name)
        return hostname

    def _event_for_task(self, task, node_name):
        task_type = task.get('type')
        status = "success" if task.get("status") == "OK" else "error"
        id = task.get('id') if task.get('id') else node_name
        user = task.get('user')
        event_title = EVENT_TYPE_TO_TITLE.get(task_type, task_type)
        resource_type = resource_type_for_event_type(task_type)
        resource_id = f'{resource_type}/{id}'
        self.log.debug(
            "Creating event for task type: %s ID: %s, resource id %s on node %s",
            task_type,
            id,
            resource_id,
            node_name,
        )

        resource = self.all_resources.get(resource_id, {})

        tags = copy.deepcopy(resource.get('tags', []))
        tags.append(f'proxmox_event_type:{task_type}')
        tags.append(f'proxmox_user:{user}')

        timestamp = task.get('endtime', get_timestamp(get_current_datetime()))
        hostname = resource.get('hostname', None)

        if resource_type != 'node':
            resource_type_format = resource.get('resource_type', '').capitalize()
            event_message = f"{resource_type_format} {resource.get('resource_name')}: {event_title} on node {node_name}"
        else:
            event_message = f"{event_title} on node {node_name}"

        event = {
            'timestamp': timestamp,
            'event_type': self.__NAMESPACE__,
            'host': hostname,
            'msg_text': event_message,
            'msg_title': event_title,
            'alert_type': status,
            'source_type_name': self.__NAMESPACE__,
            'tags': tags,
        }
        return event

    def _collect_ha_metrics(self):
        ha_response = self.http.get(f"{self.config.proxmox_server}/cluster/ha/status/current")
        ha_response_json = ha_response.json()
        ha_statuses = ha_response_json.get('data', [])
        for ha_status in ha_statuses:
            if not ha_status.get('type') == 'quorum':
                continue
            status = ha_status.get('status')
            quorate = ha_status.get('quorate')
            status_value = status == "OK"
            node = ha_status.get('node')
            tags = [f'node_status:{status}']
            self.gauge('ha.quorum', status_value, hostname=node, tags=tags)
            if isinstance(quorate, int):
                self.gauge('ha.quorate', quorate, hostname=node, tags=tags)

    def _collect_performance_metrics(self):
        metrics_response = self.http.get(f"{self.config.proxmox_server}/cluster/metrics/export")
        metrics_response_json = metrics_response.json()
        metrics = metrics_response_json.get('data', {}).get('data', [])

        for metric in metrics:
            resource_id = metric.get('id')
            resource = self.all_resources.get(resource_id, {})
            metric_value = metric.get('value')
            metric_name = metric.get('metric')
            metric_type = metric.get('type')
            metric_name_remapped = PERF_METRIC_NAME.get(metric_name)
            hostname = resource.get('hostname')
            tags = resource.get('tags', [])
            if not resource or metric_name_remapped is None:
                self.log.debug(
                    "Invalid metric entry found; metric name: %s, resource id: %s", metric_name_remapped, resource_id
                )
                continue

            metric_method = self.count if metric_type == 'derive' else self.gauge
            metric_method(metric_name_remapped, metric_value, tags=tags, hostname=hostname)

    def _collect_resource_metrics(self):
        resources_response = self.http.get(f"{self.config.proxmox_server}/cluster/resources")
        resources_response_json = resources_response.json()
        resources = resources_response_json.get("data", [])

        external_tags = []
        all_resources = {}

        for resource in resources:
            resource_type = resource.get('type')
            node = resource.get('node')
            resource_type_remapped = RESOURCE_TYPE_MAP.get(resource_type, resource_type)
            resource_id = resource.get('id')
            resource_name = resource.get('name')
            if resource_name is None:
                # some resource types don't have a name attribute
                resource_name = resource.get(resource.get('type', ''))

            resource_tags = {
                f'proxmox_type:{resource_type_remapped}',
                f'proxmox_name:{resource_name}',
                f'proxmox_id:{resource_id}',
            }

            proxmox_tags = resource.get('tags')
            if proxmox_tags:
                proxmox_tags = proxmox_tags.split(';')
                resource_tags.update(proxmox_tags)

            if node and resource_type_remapped != 'node':
                resource_tags.add(f'proxmox_node:{node}')

            pool = resource.get('pool')
            if pool and resource_type_remapped != 'pool':
                resource_tags.add(f'proxmox_pool:{pool}')

            self.gauge(
                f'{resource_type_remapped}.count',
                1,
                tags=self.base_tags + list(resource_tags),
            )

            status = resource.get("status")
            status = 1 if status in OK_STATUS else 0

            hostname = None

            if (resource_type_remapped == VM_RESOURCE or resource_type_remapped == NODE_RESOURCE) and status == 0:
                # don't collect information about powered off VMs and nodes
                continue
            elif resource_type_remapped == VM_RESOURCE and status == 1:
                vm_id = resource.get('vmid')
                hostname = self._get_vm_hostname(vm_id, resource_name, node)
            elif resource_type_remapped == NODE_RESOURCE:
                hostname = node

            tags = []
            if hostname is None:
                tags = self.base_tags + list(resource_tags)
            else:
                external_tags.append((hostname, {self.__NAMESPACE__: self.base_tags + list(resource_tags)}))

            all_resources[resource_id] = {
                'resource_type': resource_type_remapped,
                'resource_name': resource_name,
                'tags': tags,
                'hostname': hostname,
            }

            if resource_type_remapped != "pool":
                # pools don't have a status attribute
                self.gauge(
                    f'{resource_type_remapped}.up',
                    status,
                    tags,
                    hostname=hostname,
                )
            self._submit_resource_metrics(resource, tags, hostname)

        self.all_resources = all_resources
        self.set_external_tags(external_tags)

    def _collect_tasks(self):
        for resource in self.all_resources.values():
            if resource.get('resource_type') != 'node':
                continue

            node_name = resource.get('hostname')
            since = int(get_timestamp(self.last_event_collect_time))
            self.log.debug("Collecting events for node %s since %s", node_name, since)

            now = get_current_datetime()
            params = {'since': since}
            response = self.http.get(f"{self.config.proxmox_server}/nodes/{node_name}/tasks", params=params)
            response.raise_for_status()

            response_json = response.json().get("data", [])
            self.last_event_collect_time = now

            for task in response_json:
                task_type = task.get('type')

                if task_type not in self.config.collected_task_types:
                    continue

                event = self._event_for_task(task, node_name)
                self.log.trace("Submitting event %s", event)
                self.event(event)

    def check(self, _):
        try:
            response = self.http.get(f"{self.config.proxmox_server}/version")
            response.raise_for_status()

            response_json = response.json()
            version = response_json.get("data", {}).get("version")
            self.set_metadata('version', version)
            self.gauge("api.up", 1, tags=self.base_tags + ['proxmox_status:up'])

        except (HTTPError, InvalidURL, ConnectionError, Timeout, JSONDecodeError) as e:
            self.log.error(
                "Encountered an Exception when hitting the Proxmox API %s: %s", self.config.proxmox_server, e
            )
            self.gauge("api.up", 0, tags=self.base_tags + ['proxmox_status:down'])
            raise

        self._collect_resource_metrics()
        self._collect_performance_metrics()
        self._collect_ha_metrics()
        if self.config.collect_tasks:
            self._collect_tasks()
