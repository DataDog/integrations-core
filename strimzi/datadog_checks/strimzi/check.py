# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2
from datadog_checks.strimzi.config_models import ConfigMixin
from datadog_checks.strimzi.metrics import (
    CLUSTER_OPERATOR_METRICS_MAP,
    TOPIC_OPERATOR_METRICS_MAP,
    USER_OPERATOR_METRICS_MAP,
)

CLUSTER_OPERATOR_NAMESPACE = "strimzi.cluster_operator"
TOPIC_OPERATOR_NAMESPACE = "strimzi.topic_operator"
USER_OPERATOR_NAMESPACE = "strimzi.user_operator"


class StrimziCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(StrimziCheck, self).__init__(name, init_config, instances)
        self.scraper_configs = []
        self.check_initializations.appendleft(self.parse_config)

    def parse_config(self):
        cluster_operator_endpoint = self.instance.get("cluster_operator_endpoint")
        topic_operator_endpoint = self.instance.get("topic_operator_endpoint")
        user_operator_endpoint = self.instance.get("user_operator_endpoint")

        if not cluster_operator_endpoint and not topic_operator_endpoint and not user_operator_endpoint:
            raise ConfigurationError(
                "Must specify at least one of the following:"
                "`cluster_operator_endpoint`, `topic_operator_endpoint` or `user_operator_endpoint`."
            )

        if cluster_operator_endpoint:
            self.scraper_configs.append(
                self.create_config(cluster_operator_endpoint, CLUSTER_OPERATOR_NAMESPACE, CLUSTER_OPERATOR_METRICS_MAP)
            )

        if topic_operator_endpoint:
            self.scraper_configs.append(
                self.create_config(topic_operator_endpoint, TOPIC_OPERATOR_NAMESPACE, TOPIC_OPERATOR_METRICS_MAP)
            )

        if user_operator_endpoint:
            self.scraper_configs.append(
                self.create_config(user_operator_endpoint, USER_OPERATOR_NAMESPACE, USER_OPERATOR_METRICS_MAP)
            )

    def create_config(self, endpoint, namespace, metrics):
        config = copy.deepcopy(self.instance)
        config['openmetrics_endpoint'] = endpoint
        config['metrics'] = [metrics]
        config['namespace'] = namespace
        return config
