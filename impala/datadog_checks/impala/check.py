# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2
from datadog_checks.impala.config_models import ConfigMixin
from datadog_checks.impala.metrics_catalog import CATALOG_METRIC_MAP, CATALOG_METRICS_WITH_LABEL_IN_NAME
from datadog_checks.impala.metrics_daemon import DAEMON_METRIC_MAP, DAEMON_METRICS_WITH_LABEL_IN_NAME
from datadog_checks.impala.metrics_statestore import STATESTORE_METRIC_MAP

TO_SNAKE_CASE_PATTERN = re.compile('(?!^)([A-Z]+)')


class ImpalaCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'impala'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.append(self.configure_additional_transformers)

    def get_default_config(self):
        if self.instance["service_type"] == "daemon":
            return {
                "metrics": [DAEMON_METRIC_MAP],
            }

        if self.instance["service_type"] == "statestore":
            return {
                "metrics": [STATESTORE_METRIC_MAP],
            }

        if self.instance["service_type"] == "catalog":
            return {
                "metrics": [CATALOG_METRIC_MAP],
            }

        # Should not happen because this is validated at boot
        raise ConfigurationError(
            f"Unexpected value ({self.instance['service_type']}) for `service_type`; "
            f"permitted: 'daemon', 'statestore', 'catalog'"
        )

    def service_check(self, name, status, tags=None, hostname=None, message=None, raw=False):
        return super().service_check(f"{self.instance['service_type']}.{name}", status, tags, hostname, message, raw)

    def configure_transformer_with_label_in_name(self, metric_pattern, metric_spec):
        compiled_metric_pattern = re.compile(metric_pattern)

        def transform(metric, sample_data, runtime_data):
            for sample, tags, hostname in sample_data:
                groups = compiled_metric_pattern.match(sample.name).groups()

                # Exclude metrics that are not declared
                if groups[1] in metric_spec["sub_metrics"]:
                    sub_metric = metric_spec["sub_metrics"][groups[1]]
                    tags.append(
                        '{}:{}'.format(metric_spec["label_name"], TO_SNAKE_CASE_PATTERN.sub(r'_\1', groups[0]).lower())
                    )

                    method = getattr(self, sub_metric['type'])
                    method(sub_metric["new_name"], sample.value, tags=tags, hostname=hostname)

        return transform

    def configure_additional_transformers(self):
        if self.instance["service_type"] in ["catalog", "daemon"]:
            if self.instance["service_type"] == "catalog":
                metrics_with_label_in_name = CATALOG_METRICS_WITH_LABEL_IN_NAME
            else:
                metrics_with_label_in_name = DAEMON_METRICS_WITH_LABEL_IN_NAME

            for metric_pattern, metric in metrics_with_label_in_name.items():
                self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer.add_custom_transformer(
                    metric_pattern,
                    self.configure_transformer_with_label_in_name(metric_pattern, metric),
                    pattern=True,
                )
