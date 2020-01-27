# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from six.moves.urllib.parse import urlparse

from datadog_checks.base import OpenMetricsBaseCheck
from datadog_checks.base.errors import ConfigurationError

from .metrics import ADDITIONAL_METRICS_MAP, INSTANCE_DEFAULT_METRICS


class ScyllaCheck(OpenMetricsBaseCheck):
    """
    Collect Scylla metrics from Prometheus endpoint
    """

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):

        instance = instances[0]

        if 'instance_endpoint' in instance:
            endpoint = instance.get('instance_endpoint')
            namespace = 'scylla'

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
                    raise ConfigurationError(
                        'Invalid metric_groups found in scylla conf.yaml: {}'.format(', '.join(errors))
                    )

            metrics = INSTANCE_DEFAULT_METRICS + additional_metrics

        else:
            raise ConfigurationError("Must provide at least one endpoint per instance")

        tags = instance.get('tags', [])
        tags.append('endpoint_host:{}'.format(urlparse(endpoint).hostname))

        instance.update({'prometheus_url': endpoint, 'namespace': namespace, 'metrics': metrics, 'tags': tags})

        super(ScyllaCheck, self).__init__(name, init_config, instances=[instance])
