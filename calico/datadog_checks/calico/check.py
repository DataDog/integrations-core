from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRIC_MAP


class CalicoCheck(OpenMetricsBaseCheckV2):
    def __init__(self, name, init_config, instances=None):

        super(CalicoCheck, self).__init__(
            name,
            init_config,
            instances,
        )

    def get_default_config(self):
        return {'namespace': 'calico', 'metrics': [METRIC_MAP]}
