# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY2
from six.moves.urllib.parse import urlparse

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck

from .metrics import ADDITIONAL_METRICS_MAP, INSTANCE_DEFAULT_METRICS


class ScyllaCheck(OpenMetricsBaseCheck):
    """
    This is a legacy implementation that will be removed at some point, refer to check.py for the new implementation.
    """

    METRIC_PREFIX = 'scylla.'

    """
    Collect Scylla metrics from Prometheus endpoint
    """

    DEFAULT_METRIC_LIMIT = 0

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if instance.get('openmetrics_endpoint'):
            if PY2:
                raise ConfigurationError(
                    'This version of the integration is only available when using Python 3. '
                    'Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3/ '
                    'for more information or use the older style config.'
                )
            # TODO: when we drop Python 2 move this import up top
            from .scylla_v2 import ScyllaCheckV2

            return ScyllaCheckV2(name, init_config, instances)
        else:
            return super(ScyllaCheck, cls).__new__(cls)

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
