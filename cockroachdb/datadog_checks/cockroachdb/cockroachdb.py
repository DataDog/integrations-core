# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck
from .metrics import METRIC_MAP


class CockroachdbCheck(OpenMetricsBaseCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(CockroachdbCheck, self).__init__(
            name,
            init_config,
            agentConfig,
            instances,
            default_instances={
                'cockroachdb': {
                    'prometheus_url': 'http://localhost:8080/_status/vars',
                    'namespace': 'cockroachdb',
                    'metrics': [METRIC_MAP],
                    'send_histograms_buckets': True,
                }
            },
            default_namespace='cockroachdb',
        )
