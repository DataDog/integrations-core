# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

from datadog_checks.base import OpenMetricsBaseCheck
from datadog_checks.base.errors import CheckException

from .metrics import ADDITIONAL_METRICS_MAP, INSTANCE_DEFAULT_METRICS, MANAGER_METRICS


class ScyllaCheck(OpenMetricsBaseCheck):
    """
    Collect Scylla metrics from Prometheus endpoint
    """

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        scylla_instances = []

        for instance in instances:
            if 'instance_endpoint' in instance:
                scylla_instance = deepcopy(instance)
                endpoint = instance.get('instance_endpoint')

                # extract additional metrics requested and validate the correct names
                metric_groups = instance.get('metric_groups', [])
                additional_metrics = []
                if metric_groups:
                    errors = []
                    for group in metric_groups:
                        try:
                            additional_metrics.append(ADDITIONAL_METRICS_MAP[group])
                        except KeyError:
                            errors.append(group)

                    if errors:
                        raise CheckException(
                            'Invalid metric_groups found in scylla conf.yaml: {}'.format(', '.join(errors))
                        )

                scylla_instance.update(
                    {
                        'prometheus_url': endpoint,
                        'namespace': 'scylla',
                        'metrics': INSTANCE_DEFAULT_METRICS + additional_metrics,
                        'prometheus_timeout': instance.get('timeout', 10),
                    }
                )
                scylla_instances.append(scylla_instance)

            if 'manager_endpoint' in instance:
                manager_instance = deepcopy(instance)

                manager_instance.update(
                    {
                        'prometheus_url': instance.get('manager_endpoint'),
                        'namespace': 'scylla.manager',
                        'metrics': [MANAGER_METRICS],
                        'prometheus_timeout': instance.get('timeout', 10),
                    }
                )
                scylla_instances.append(manager_instance)

        super(ScyllaCheck, self).__init__(name, init_config, instances=scylla_instances)

    def check(self, instance):
        """
        Process all configured endpoints
        """
        instance_endpoint = instance.get('instance_endpoint')
        if instance_endpoint:
            instance_config = self.config_map[instance_endpoint]

            self.process(instance_config)

        manager_endpoint = instance.get('manager_endpoint')
        if manager_endpoint:
            manager_config = self.config_map[manager_endpoint]

            self.process(manager_config)
