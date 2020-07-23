# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pprint import pprint
from typing import Any

from requests.exceptions import HTTPError

from datadog_checks.base import AgentCheck, ConfigurationError

from .api import MarkLogicApi
from .config import Config
from .constants import RESOURCE_TYPES
from .parsers.health import parse_summary_health
from .parsers.status import parse_summary_status_base_metrics, parse_summary_status_resource_metrics
from .parsers.storage import parse_summary_storage_base_metrics


class MarklogicCheck(AgentCheck):
    __NAMESPACE__ = 'marklogic'
    SERVICE_CHECK_CONNECT = 'can_connect'

    def __init__(self, name, init_config, instances):
        super(MarklogicCheck, self).__init__(name, init_config, instances)

        url = self.instance.get('url')
        if not url:
            raise ConfigurationError("url is a required configuration.")

        self.api = MarkLogicApi(self.http, url)

        self.config = Config(self.instance)

        self.collectors = [
            self.collect_summary_status_base_metrics,
            self.collect_summary_status_resource_metrics,
            self.collect_summary_storage_base_metrics,
            self.collect_per_resource_status_metrics,
        ]

        self.resources_to_monitor = None  # Refreshed at each check

    def check(self, _):
        # type: (Any) -> None
        # TODO: Handle errors:
        #       - X Continue if one of the processor fail
        #       - Add service check (can connect, status service check)
        # No need to query base requests metrics, they are already collect in by process_base_status
        # self.process_requests_metrics_by_resource()

        self.resources_to_monitor = self.get_resources_to_monitor()

        for collector in self.collectors:
            try:
                collector()
            except Exception:
                self.log.exception("Collector %s failed while collecting metrics", collector.__name__)

        self.submit_service_checks()

    def collect_summary_status_resource_metrics(self):
        # type: () -> None
        """
        Collect Summary Status Resource Metrics.

        Only necessary for forest resource metrics. Other resources metrics are already collected via
        `collect_summary_status_base_metrics`.
        """
        for resource_type in ['forest']:
            res_meta = RESOURCE_TYPES[resource_type]
            data = self.api.get_status_data(res_meta['plural'])
            metrics = parse_summary_status_resource_metrics(resource_type, data, self.config.tags)
            self.submit_metrics(metrics)

    def collect_summary_status_base_metrics(self):
        # type: () -> None
        """
        Collect Summary Status Base Metrics.

        Includes:
          - Summary Request Metrics (Same metrics as `/requests`)
          - Summary Host Metrics (Same metrics as `/hosts`)
          - Summary Server Metrics (Same metrics as `/servers`)
          - Summary Transaction Metrics
        """
        data = self.api.get_status_data()
        metrics = parse_summary_status_base_metrics(data, self.config.tags)
        self.submit_metrics(metrics)

    def collect_summary_storage_base_metrics(self):
        # type: () -> None
        """
        Collect Base Storage Metrics
        """
        data = self.api.get_forests_storage_data()
        metrics = parse_summary_storage_base_metrics(data, self.config.tags)
        self.submit_metrics(metrics)

    def collect_per_resource_status_metrics(self):
        # type: () -> None
        """
        Collect Per Resource Status Metrics.
        """
        pprint(self.resources_to_monitor)

    def get_resources_to_monitor(self):
        # type: () -> None
        resources = self.api.get_resources()
        pprint(self.config.resource_filters)
        pprint(resources)
        return []

    def submit_metrics(self, metrics):
        for metric_type, metric_name, value_data, tags in metrics:
            getattr(self, metric_type)(metric_name, value_data, tags=tags)

    def submit_service_checks(self):
        # type: () -> None
        try:
            data = self.api.get_health()
            service_checks = parse_summary_health(data, self.config.tags)

            for name, status, message, tags in service_checks:
                self.service_check(name, status, tags=tags, message=message)
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, self.config.tags)
        except HTTPError:
            # Couldn't access the health endpoint
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, self.config.tags)
        except Exception:
            # Couldn't parse the resource health
            self.log.exception('Failed to parse the resources health')


"""
Design

Metric naming

marklogic.status.<METRIC_NAME> e.g. marklogic.status.backup-read-bytes

tags by object type:
    - cluster
    - hosts
    - database
    - forest
    - groups

Query Metrics
    - http://localhost:8002/dashboard/query
    - Example queries:
        - http://localhost:8002/manage/v2/requests?format=json (cluster level)
        - http://localhost:8002/manage/v2/requests?format=json&server-id=Admin&group-id=Default
        - http://localhost:8002/manage/v2/requests?format=json&group-id=Default
        - http://localhost:8002/manage/v2/requests?format=json&host-id=2871b05b4bdc
    - metric name: marklogic.query_summary.<METRIC_NAME>
    - metric name: marklogic.query.<METRIC_NAME>

Rates & Loads Metrics aka Status metrics (view=status)
    - http://localhost:8002/dashboard/load/
    - Example queries:
        - http://localhost:8002/manage/v2/hosts?view=status
        - http://localhost:8002/manage/v2/hosts?view=status&format=json (cluster level)
        - http://localhost:8002/manage/v2/forests/Security?view=status&format=json
        - http://localhost:8002/manage/v2/databases/Extensions?view=status&format=json
        - http://localhost:8002/manage/v2/hosts/2871b05b4bdc?view=status&format=json
        - http://localhost:8002/manage/v2/transactions?format=json
            (already in http://localhost:8002/manage/v2/hosts?view=status)
        - http://localhost:8002/manage/v2/servers?view=status&format=json
            (already in http://localhost:8002/manage/v2/hosts?view=status)
    - metric name: marklogic.status_summary.<METRIC_NAME>
    - metric name: marklogic.status.<METRIC_NAME>

Storage Metrics
    - http://localhost:8002/dashboard/disk-space/
    - Example queries:
        - http://localhost:8002/manage/v2/forests?format=json&view=storage
        - http://localhost:8002/manage/v2/forests?format=json&view=storage&database-id=Last-Login
        - http://localhost:8002/manage/v2/forests?format=json&view=storage&forest-id=Last-Login
        - http://localhost:8002/manage/v2/forests?format=json&view=storage&database-id=Security
    - metric name: marklogic.storage_summary.<METRIC_NAME>
    - metric name: marklogic.storage.<METRIC_NAME>

"""
