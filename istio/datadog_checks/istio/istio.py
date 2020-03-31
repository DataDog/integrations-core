# (C) Datadog, Inc. 2020 - Present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck

from .legacy_1_4 import LegacyIstioCheck_1_4
from .metrics import ISTIOD_METRICS


class Istio(OpenMetricsBaseCheck):
    """
    Check the offsets and lag of Kafka consumers.
    This check also returns broker highwater offsets.
    """

    def __init__(self, name, init_config, instances):
        instance = instances[0]
        instance.update(
            {
                'prometheus_url': instance.get('istiod_endpoint'),
                'namespace': 'istio',
                'metrics': [ISTIOD_METRICS],
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
        scraper_config = self.get_scraper_config(instance)
        self.process(scraper_config)
