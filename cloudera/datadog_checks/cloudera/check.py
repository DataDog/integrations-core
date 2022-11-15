# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
import time

from datadog_checks.base import AgentCheck

from .client_factory import make_api_client
from .queries import TIMESERIES_QUERIES


class ClouderaCheck(AgentCheck):
    __NAMESPACE__ = 'cloudera'

    def __init__(self, name, init_config, instances):
        super(ClouderaCheck, self).__init__(name, init_config, instances)

        self.client, self._error = make_api_client(self, self.instance)
        if self.client is None:
            self.error("API Client is none: %s", self._error)
            self.service_check("can_connect", ClouderaCheck.CRITICAL)

    def run_timeseries_checks(self):
        to_time = datetime.datetime.fromtimestamp(time.time())
        from_time = datetime.datetime.fromtimestamp(time.time() - 6000)

        # For each timeseries query, get the metrics
        for query in TIMESERIES_QUERIES:
            responses = self.client.query_time_series(query=query['query_string'], from_time=from_time, to_time=to_time)

            for response in responses:
                value = response.data[0].value
                attributes = response.metadata.attributes

                # TODO: make this compatible with Py2
                tags = [f"{datadog_tag}:{attributes[attribute]}" for datadog_tag, attribute in query['tags']]

                category = attributes['category'].lower()
                self.gauge(f"{category}.{query['metric_name']}", value, tags=tags)
    # https://cod--qfdcinkqrzw-gateway.agent-in.jfha-h5rc.a0.cloudera.site/cod--qfdcinkqrzw/cdp-proxy/hbase/webui/logs/hbase-cmf-hbase-MASTER-cod--qfdcinkqrzw-master1.agent-in.jfha-h5rc.a0.cloudera.site.log.out?host=cod--qfdcinkqrzw-master1.agent-in.jfha-h5rc.a0.cloudera.site&port=16010

    def run_service_checks(self):
        # Get the clusters
        # ClustersResourceApi

        # For each cluster, get the services
        # ServicesResourceApi

        # Structure:
        # Cluster
        # - Service
        #   - Nameservice
        #   - Role
        # - Host

        # Get host metrics
        # HostsResourceApi

        # get nameservice metrics
        # NameservicesResourceApi

        # get role metrics
        # RolesResourceApi

        # get service metrics
        # ServicesResourceApi

        self.service_check("can_connect", ClouderaCheck.OK)

    def check(self, _):
        # Run through the list of default timeseries metrics first
        self.run_timeseries_checks()

        # Next steps: try to get cluster metrics and see how to structure hierarchy

        # Get the service checks of cluster, service, nameservice, role, and host
        self.run_service_checks()

        # Run any custom queries

        # at the end, output can_connect
