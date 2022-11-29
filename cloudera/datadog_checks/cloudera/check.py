# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import six

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.cloudera.api_client_factory import make_api_client
from datadog_checks.cloudera.queries import TIMESERIES_QUERIES


class ClouderaCheck(AgentCheck):
    __NAMESPACE__ = 'cloudera'

    def __init__(self, name, init_config, instances):
        if six.PY2:
            raise ConfigurationError(
                "This version of the integration is only available when using py3. "
                "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                "for more information."
            )

        super(ClouderaCheck, self).__init__(name, init_config, instances)
        self._api_client, self._error = make_api_client(self, self.instance)

    def check(self, _):
        if self._api_client is None:
            self.log.debug('Api Client is None: %s', self._error)
            self.service_check("can_connect", AgentCheck.CRITICAL)
        else:
            if self.instance.get('run_timeseries', False):
                self._run_timeseries_checks()
            else:
                self._api_client.collect_data()

    def _run_timeseries_checks(self):
        # For each timeseries query, get the metrics
        # TODO: Running these metrics cause the execution time to be high, run async?
        for query in TIMESERIES_QUERIES:
            items = self._api_client.run_timeseries_query(query=query['query_string'])
            for item in items:
                if not item.data:
                    self.log.debug("Data for entity %s is empty", item.metadata.entity_name)
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
                        self.log.debug("no %s tag for metric %s", datadog_tag, item.metadata.entity_name)

                category = attributes['category'].lower()
                self.log.debug("metric: %s", f"{category}.{query['metric_name']}")
                self.log.debug("value: %s", value)
                self.log.debug("tags: %s", tags)
                self.gauge(f"{category}.{query['metric_name']}", value, tags=tags)
