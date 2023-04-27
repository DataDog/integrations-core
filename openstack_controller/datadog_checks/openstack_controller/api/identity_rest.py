# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.openstack_controller.metrics import (
    KEYSTONE_DOMAINS_METRICS,
    KEYSTONE_DOMAINS_METRICS_PREFIX,
    get_normalized_metrics,
)


class IdentityRest:
    def __init__(self, log, http, endpoint):
        self.log = log
        self.http = http
        self.endpoint = endpoint

    def get_response_time(self):
        response = self.http.get('{}'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.elapsed.total_seconds() * 1000

    def get_domains(self):
        response = self.http.get('{}/domains'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        domain_metrics = {}
        for domain in response.json()['domains']:
            domain_metrics[domain['id']] = {
                'name': domain['name'],
                'metrics': get_normalized_metrics(domain, KEYSTONE_DOMAINS_METRICS_PREFIX, KEYSTONE_DOMAINS_METRICS),
            }
        return domain_metrics

    def get_projects(self):
        response = self.http.get('{}/projects'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['projects']

    def get_users(self):
        response = self.http.get('{}/users'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['users']

    def get_groups(self):
        response = self.http.get('{}/groups'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['groups']

    def get_group_users(self, group_id):
        response = self.http.get('{}/groups/{}/users'.format(self.endpoint, group_id))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['users']

    def get_services(self):
        response = self.http.get('{}/services'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['services']

    def get_registered_limits(self):
        response = self.http.get('{}/registered_limits'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['registered_limits']

    def get_limits(self):
        response = self.http.get('{}/limits'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['limits']
