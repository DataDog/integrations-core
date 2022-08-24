# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2
from datadog_checks.impala.config_models import ConfigMixin
from datadog_checks.impala.metrics_catalog import CATALOG_METRIC_MAP
from datadog_checks.impala.metrics_daemon import DAEMON_METRIC_MAP
from datadog_checks.impala.metrics_statestore import STATESTORE_METRIC_MAP


class ImpalaCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'impala'

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
            f"service_type unexpected value ({self.instance['service_type']}); "
            f"permitted: 'daemon', 'statestore', 'catalog'"
        )

    def service_check(self, name, status, tags=None, hostname=None, message=None, raw=False):
        return super().service_check(f"{self.instance['service_type']}.{name}", status, tags, hostname, message, raw)
