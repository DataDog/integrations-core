# (C) Datadog, Inc. 2020 - Present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.base import is_affirmative
from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck

from .legacy_1_4 import LegacyIstioCheck_1_4


class Istio(OpenMetricsBaseCheck):
    """
    Check the offsets and lag of Kafka consumers.
    This check also returns broker highwater offsets.
    """

    __NAMESPACE__ = 'istio'

    def __init__(self, name, init_config, instances):

        self.log.info('Collecting metrics from Istiod deployment (Istio v1.5+)')

        self.instance.update(
            {
                'prometheus_url': self.instance.get('istiod_endpoint'),
                'namespace': 'istio.istiod',
                'metrics': [],
                'metadata_metric_name': 'istio_build',
                'metadata_label_map': {'version': 'tag'},
            }
        )
        super(Istio, self).__init__(name, init_config, instances)

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if is_affirmative(instance.get('istiod_endpoint')):
            return super(Istio, cls).__new__(cls)
        else:
            return LegacyIstioCheck_1_4(name, init_config, instances)

    def check(self, instance):
        raise NotImplementedError()
