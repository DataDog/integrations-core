# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six.moves.urllib.parse import urlparse

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck

from .metrics import ADDITIONAL_METRICS_MAP, INSTANCE_DEFAULT_METRICS


class ScyllaCheck(OpenMetricsBaseCheck):
    """
    Collect Scylla metrics from Prometheus endpoint
    """

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):

        instance = instances[0]

        endpoint = instance.get('prometheus_url')
        if endpoint is None:
            raise ConfigurationError("Unable to find prometheus URL in config file.")

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

        tags = instance.get('tags', [])

        # include hostname:port for server tag
        tags.append('server:{}'.format(urlparse(endpoint).netloc))

        instance.update(
            {
                'prometheus_url': endpoint,
                'namespace': 'scylla',
                'metrics': metrics,
                'tags': tags,
                'metadata_metric_name': 'scylla_scylladb_current_version',
                'metadata_label_map': {'version': 'version'},
                'send_histograms_buckets': True,  # Default, but ensures we collect histograms sent by Scylla.
            }
        )

        super(ScyllaCheck, self).__init__(name, init_config, [instance])
