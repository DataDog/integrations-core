# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six.moves.urllib.parse import urlparse

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck
from datadog_checks.base.errors import CheckException

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
            # needed to guard for Python2
            # empty endpoint will raise CheckException at init, but Py2 urlparse will raise AttributeError instead
            raise CheckException("Unable to find prometheus URL in config file.")

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

        tags = instance.get('tags', [])
        tags.append('endpoint_server:{}'.format(urlparse(endpoint).hostname))

        instance.update(
            {
                'prometheus_url': endpoint,
                'namespace': namespace,
                'metrics': metrics,
                'tags': tags,
                'metadata_metric_name': 'scylla_scylladb_current_version',
                'metadata_label_map': {'version': 'version'},
            }
        )

        super(ScyllaCheck, self).__init__(name, init_config, [instance])
