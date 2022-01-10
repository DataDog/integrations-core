# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRIC_MAP


class KongCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'kong'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self.check_initializations.append(self.configure_additional_transformers)

    def get_default_config(self):
        return {'metrics': [METRIC_MAP]}

    def configure_transformer_upstream_target_health(self):
        status_map = {'healthy': self.OK, 'unhealthy': self.CRITICAL, 'dns_error': self.CRITICAL}

        def service_check(metric, sample_data, runtime_data):
            for sample, tags, hostname in sample_data:
                # value is 1 when state is populated
                if sample.value != 1:
                    continue

                state = sample.labels['state']
                if state == 'healthchecks_off':
                    continue

                tags.remove('state:{}'.format(state))
                self.service_check(
                    'upstream.target.health', status_map.get(state, self.UNKNOWN), tags=tags, hostname=hostname
                )

        return service_check

    def configure_additional_transformers(self):
        transformer_data = self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer.transformer_data

        transformer_data['kong_upstream_target_health'] = None, self.configure_transformer_upstream_target_health()
