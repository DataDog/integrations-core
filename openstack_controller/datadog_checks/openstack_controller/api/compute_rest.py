# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from datadog_checks.openstack_controller.metrics import (
    NOVA_FLAVOR_METRICS,
    NOVA_HYPERVISOR_METRICS,
    NOVA_HYPERVISOR_METRICS_PREFIX,
    NOVA_LIMITS_METRICS,
    NOVA_METRICS_PREFIX,
    NOVA_QUOTA_SETS_METRICS,
    NOVA_SERVER_METRICS,
    NOVA_SERVER_METRICS_PREFIX,
    get_normalized_metrics,
)


def _load_averages_from_uptime(uptime):
    """Parse u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n'"""
    uptime = uptime.strip()
    load_averages = uptime[uptime.find('load average:') :].split(':')[1].strip().split(',')
    load_averages = [float(load_avg) for load_avg in load_averages]
    return load_averages


class ComputeRest:
    def __init__(self, log, http, endpoint):
        self.log = log
        self.http = http
        self.endpoint = endpoint
        self.log.debug("compute endpoint: %s", endpoint)

    def get_response_time(self):
        response = self.http.get('{}'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.elapsed.total_seconds() * 1000

    def get_limits(self):
        response = self.http.get('{}/limits'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return get_normalized_metrics(response.json(), NOVA_METRICS_PREFIX, NOVA_LIMITS_METRICS)

    def get_quota_set(self, project_id):
        response = self.http.get('{}/os-quota-sets/{}'.format(self.endpoint, project_id))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        quota_set = {
            'id': response.json()['quota_set']['id'],
            'metrics': get_normalized_metrics(response.json(), NOVA_METRICS_PREFIX, NOVA_QUOTA_SETS_METRICS),
        }
        return quota_set

    def get_services(self):
        response = self.http.get('{}/os-services'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        services = []
        for service in response.json().get('services'):
            service_name = service.get('binary').replace('-', '_')
            is_down = service.get('state') is not None and service.get('state') == 'down'
            is_enabled = service.get('status') == 'enabled'
            is_up = not (is_down and is_enabled)
            services.append(
                {
                    'name': service_name,
                    'is_up': is_up,
                    'zone': service.get('zone'),
                    'host': service.get('host'),
                    'status': service.get('status'),
                    'id': service.get('id'),
                    'state': service.get('state'),
                }
            )
        return services

    def get_servers(self, project_id):
        response = self.http.get('{}/servers/detail?project_id={}'.format(self.endpoint, project_id))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        server_metrics = {}
        for server in response.json()['servers']:
            server_metrics[server['id']] = {
                'name': server['name'],
                'status': server['status'].lower(),
                'hypervisor_hostname': server['OS-EXT-SRV-ATTR:hypervisor_hostname'],
                'instance_hostname': server.get('OS-EXT-SRV-ATTR:hostname'),
                'metrics': get_normalized_metrics(server, NOVA_SERVER_METRICS_PREFIX, NOVA_SERVER_METRICS),
            }
            flavor = server.get('flavor')
            if flavor:
                flavor_id = flavor.get('id')
                if flavor_id is not None:
                    flavor_metrics = self._get_flavor_id(flavor_id)
                    server_metrics[server['id']]['flavor_name'] = flavor_metrics[flavor_id]['name']
                    server_metrics[server['id']]['metrics'].update(
                        get_normalized_metrics(
                            flavor_metrics[flavor_id]['metrics'],
                            f'{NOVA_SERVER_METRICS_PREFIX}.flavor',
                            NOVA_SERVER_METRICS,
                        )
                    )
                else:
                    server_metrics[server['id']]['flavor_name'] = flavor.get('original_name')
                    server_metrics[server['id']]['metrics'].update(
                        get_normalized_metrics(flavor, f'{NOVA_SERVER_METRICS_PREFIX}.flavor', NOVA_SERVER_METRICS)
                    )
            try:
                response = self.http.get('{}/servers/{}/diagnostics'.format(self.endpoint, server['id']))
                response.raise_for_status()
                self.log.debug("response: %s", response.json())
                server_metrics[server['id']]['metrics'].update(
                    get_normalized_metrics(response.json(), NOVA_SERVER_METRICS_PREFIX, NOVA_SERVER_METRICS)
                )
            except Exception as e:
                self.log.info(
                    "Could not query the server diagnostics endpoint for server %s, "
                    "perhaps it is a bare metal machine: %s",
                    server.get("id", None),
                    e,
                )
        return server_metrics

    def get_flavors(self):
        response = self.http.get('{}/flavors/detail'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        flavor_metrics = {}
        for flavor in response.json()['flavors']:
            flavor_metrics[flavor['id']] = {
                'name': flavor['name'],
                'metrics': get_normalized_metrics(flavor, f'{NOVA_METRICS_PREFIX}.flavor', NOVA_FLAVOR_METRICS),
            }
        return flavor_metrics

    def _get_flavor_id(self, flavor_id):
        response = self.http.get('{}/flavors/{}'.format(self.endpoint, flavor_id))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        flavor_metrics = {}
        flavor = response.json()['flavor']
        flavor_metrics[flavor['id']] = {'name': flavor['name'], 'metrics': {}}
        for key, value in flavor.items():
            metric_key = re.sub(r'((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', key).lower().replace("-", "_")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                flavor_metrics[flavor['id']]['metrics'][metric_key] = value
            elif isinstance(value, str):
                try:
                    flavor_metrics[flavor['id']]['metrics'][metric_key] = int(value) if value else 0
                except ValueError:
                    pass
        return flavor_metrics

    def get_hypervisors(self):
        response = self.http.get('{}/os-hypervisors/detail?with_servers=true'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        hypervisors_detail_metrics = {}
        for hypervisor in response.json()['hypervisors']:
            hypervisors_detail_metrics[str(hypervisor['id'])] = {
                'name': hypervisor['hypervisor_hostname'],
                'state': hypervisor.get('state'),
                'type': hypervisor['hypervisor_type'],
                'status': hypervisor['status'],
                'metrics': get_normalized_metrics(hypervisor, NOVA_HYPERVISOR_METRICS_PREFIX, NOVA_HYPERVISOR_METRICS),
            }
            uptime = hypervisor.get('uptime')
            load_averages = []
            if uptime:
                load_averages = _load_averages_from_uptime(uptime)
            else:
                try:
                    response_uptime = self.http.get(
                        '{}/os-hypervisors/{}/uptime'.format(self.endpoint, hypervisor['id'])
                    )
                    if 200 <= response_uptime.status_code < 300:
                        self.log.debug("response uptime: %s", response_uptime.json())
                        uptime = response_uptime.json().get('hypervisor', {}).get('uptime')
                        if uptime:
                            load_averages = _load_averages_from_uptime(uptime)
                except Exception as e:
                    self.log.info(
                        "Could not query the uptime for hypervisor %s, perhaps it is a bare metal: %s",
                        hypervisor.get('id'),
                        e,
                    )

            if load_averages and len(load_averages) == 3:
                for i, avg in enumerate([1, 5, 15]):
                    hypervisors_detail_metrics[str(hypervisor['id'])]['metrics'][
                        f"{NOVA_HYPERVISOR_METRICS_PREFIX}.load_{avg}"
                    ] = load_averages[i]
        return hypervisors_detail_metrics

    def get_os_aggregates(self):
        response = self.http.get('{}/os-aggregates'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        os_aggregates = {}
        for aggregate in response.json()['aggregates']:
            os_aggregates[str(aggregate['id'])] = {
                'name': aggregate['name'],
                'availability_zone': aggregate['availability_zone'],
                'hosts': aggregate['hosts'],
            }
        return os_aggregates
