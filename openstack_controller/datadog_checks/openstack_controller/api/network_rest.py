# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.openstack_controller.metrics import (
    NEUTRON_AGENTS_METRICS,
    NEUTRON_AGENTS_METRICS_PREFIX,
    NEUTRON_QUOTAS_METRICS,
    NEUTRON_QUOTAS_METRICS_PREFIX,
    get_normalized_metrics,
)


class NetworkRest:
    def __init__(self, log, http, endpoint):
        self.log = log
        self.http = http
        self.endpoint = endpoint

    def get_response_time(self):
        response = self.http.get('{}'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.elapsed.total_seconds() * 1000

    def get_quotas(self, project_id):
        response = self.http.get('{}/v2.0/quotas/{}'.format(self.endpoint, project_id))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return get_normalized_metrics(response.json()['quota'], NEUTRON_QUOTAS_METRICS_PREFIX, NEUTRON_QUOTAS_METRICS)

    def get_agents(self):
        response = self.http.get('{}/v2.0/agents'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        agents_metrics = {}
        for agent in response.json()['agents']:
            agents_metrics[agent['id']] = {
                'name': agent['binary'],
                'host': agent['host'],
                'availability_zone': agent['availability_zone'],
                'type': agent['agent_type'],
                'metrics': get_normalized_metrics(agent, NEUTRON_AGENTS_METRICS_PREFIX, NEUTRON_AGENTS_METRICS),
            }
        return agents_metrics
