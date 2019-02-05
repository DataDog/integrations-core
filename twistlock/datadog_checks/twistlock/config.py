# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from copy import deepcopy

class Config:

    STANDARD_METRICS = {
        'twistlock_totalDefenders': 'total_defenders',
        'twistlock_activeDefenders': 'active_defenders',
        'twistlock_images_critical_vulnerabilities': 'images.critical_vulnerabilities',
        'twistlock_images_high_vulnerabilities': 'images.high_vulnerabilities',
        'twistlock_images_medium_vulnerabilities': 'images.medium_vulnerabilities',
        'twistlock_images_low_vulnerabilities': 'images.low_vulnerabilities',
        'twistlock_hosts_critical_vulnerabilities': 'hosts.critical_vulnerabilities',
        'twistlock_hosts_high_vulnerabilities': 'hosts.high_vulnerabilities',
        'twistlock_hosts_medium_vulnerabilities': 'hosts.medium_vulnerabilities',
        'twistlock_hosts_low_vulnerabilities': 'hosts.low_vulnerabilities',
        'twistlock_serverless_critical_vulnerabilities': 'serverless.critical_vulnerabilities',
        'twistlock_serverless_high_vulnerabilities': 'serverless.high_vulnerabilities',
        'twistlock_serverless_medium_vulnerabilities': 'serverless.medium_vulnerabilities',
        'twistlock_serverless_low_vulnerabilities': 'serverless.low_vulnerabilities',
        'twistlock_images_critical_compliance': 'images.critical_compliance',
        'twistlock_images_high_compliance': 'images.high_compliance',
        'twistlock_images_medium_compliance': 'images.medium_compliance',
        'twistlock_images_low_compliance': 'images.low_compliance',
        'twistlock_containers_critical_compliance': 'containers.critical_compliance',
        'twistlock_containers_high_compliance': 'containers.high_compliance',
        'twistlock_containers_medium_compliance': 'containers.medium_compliance',
        'twistlock_containers_low_compliance': 'containers.low_compliance',
        'twistlock_hosts_critical_compliance': 'hosts.critical_compliance',
        'twistlock_hosts_high_compliance': 'hosts.high_compliance',
        'twistlock_hosts_medium_compliance': 'hosts.medium_compliance',
        'twistlock_hosts_low_compliance': 'hosts.low_compliance',
        'twistlock_serverless_critical_compliance': 'serverless.critical_compliance',
        'twistlock_serverless_high_compliance': 'serverless.high_compliance',
        'twistlock_serverless_medium_compliance': 'serverless.medium_compliance',
        'twistlock_serverless_low_compliance': 'serverless.low_compliance',
        'twistlock_active_app_firewalls': 'active_app_firewalls',
        'twistlock_app_firewall_events': 'app_firewall_events',
        'twistlock_network_firewall_events': 'network_firewall_events',
        'twistlock_protected_containers': 'protected_containers',
        'twistlock_container_runtime_events': 'container_runtime_events',
        'twistlock_host_runtime_events': 'host_runtime_events',
        'twistlock_access_events': 'access_events',
        'twistlock_api_requests': 'api_requests',
        'twistlock_defender_events': 'defender_events',
    }

    NAMESPACE = 'twistlock'

    def __init__(self, instance):
        self.instance = instance

        self.prometheus_url = instance.get('prometheus_url')
        self.username = instance.get('username')
        self.password = instance.get('password')
        self.send_monotonic_counter = instance.get('send_monotonic_counter', True)
        self.health_service_check = instance.get('health_service_check', True)
        self.tags = instance.get('tags', [])

        self._generate_prometheus_instance()

    @property
    def prometheus_instance(self):
        return deepcopy(self._prometheus_instance)

    def _generate_prometheus_instance(self):
        self._prometheus_instance = deepcopy(self.instance)
        self._prometheus_instance.update({
            'namespace': self.NAMESPACE,
            'prometheus_url': self.prometheus_url,
            'label_to_hostname': self.prometheus_url,
            'username': self.username,
            'password': self.password,
            'send_monotonic_counter': self.send_monotonic_counter,
            'health_service_check': self.health_service_check,
            'custom_tags': self.tags,
            'metrics': [self.STANDARD_METRICS],
        })
