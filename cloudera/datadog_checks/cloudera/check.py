# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY2
from .api_client_factory import make_api_client

from datadog_checks.base import AgentCheck, ConfigurationError

from .common import (
    API_ENTITY_STATUS,
    CAN_CONNECT,
    CLUSTER_HEALTH,
    CLUSTERS_RESOURCE_API,
    HOST_HEALTH,
    ROLE_HEALTH,
    SERVICES_RESOURCE_API,
)
from .queries import TIMESERIES_QUERIES
from .config_models import ConfigMixin


class ClouderaCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'cloudera'

    def __init__(self, name, init_config, instances):
        if PY2:
            raise ConfigurationError(
                "This version of the integration is only available when using py3. "
                "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                "for more information."
            )

        super(ClouderaCheck, self).__init__(name, init_config, instances)
        self.client = None
        self.check_initializations.append(self._create_client)


    def _create_client(self):
        try:
            client = make_api_client(self, self.config)
        except Exception as e:
            self.log.error(f"Cloudera API Client is none: {e}")
            self.service_check(CAN_CONNECT, AgentCheck.CRITICAL)
            raise

        self.client = client
        self.custom_tags = self.config.tags  # TODO: Don't need self.custom_tags

    def check(self, _):
        if self.instance.get('run_timeseries', False):
            self._run_timeseries_checks()
        else:
            self.client.collect_data()

    def _run_timeseries_checks(self):
        # For each timeseries query, get the metrics
        # TODO: Running these metrics cause the execution time to be high, run async?
        for query in TIMESERIES_QUERIES:
            items = self.client.run_timeseries_query(query=query['query_string'])
            for item in items:
                if not item.data:
                    self.log.debug(f"Data for entity {item.metadata.entity_name} is empty")
                    continue

                self.log.debug("item: %s", item)
                value = item.data[0].value
                attributes = item.metadata.attributes

                # TODO: Add custom tags to this
                tags = []
                for datadog_tag, attribute in query['tags']:
                    try:
                        tags.append(f"{datadog_tag}:{attributes[attribute]}")
                    except Exception:
                        self.log.debug(f"no {datadog_tag} tag for metric {item.metadata.entity_name}")

                category = attributes['category'].lower()
                self.log.debug("metric: %s", f"{category}.{query['metric_name']}")
                self.log.debug("value: %s", value)
                self.log.debug("tags: %s", tags)
                self.gauge(f"{category}.{query['metric_name']}", value, tags=tags)
