# (C) Datadog, Inc. 2018-Present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck

from .legacy_1_4 import LegacyIstioCheck_1_4
from .metrics import ISTIOD_METRICS


class Istio(OpenMetricsBaseCheck):

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        instance = instances[0]

        if instance.get('istio_mesh_endpoint'):
            raise ConfigurationError("istio_mesh_endpoint needs to be configured in a separate instance.")

        # Support additional configured metric mappings
        metrics = instance.get('metrics', []) + [ISTIOD_METRICS]

        instance.update(
            {
                'prometheus_url': instance.get('istiod_endpoint'),
                'namespace': 'istio',
                'metrics': metrics,
                'metadata_metric_name': 'istio_build',
                'metadata_label_map': {'version': 'tag'},
            }
        )

        super(Istio, self).__init__(name, init_config, instances)

    def __new__(cls, name, init_config, instances):
        instance = instances[0]
        if instance.get('istiod_endpoint'):
            return super(Istio, cls).__new__(cls)
        else:
            return LegacyIstioCheck_1_4(name, init_config, instances)

    def check(self, instance):
        self.log.info("Collecting metrics from istiod deployment, all other endpoints are ignored.")
        scraper_config = self.get_scraper_config(instance)
        self.process(scraper_config)
