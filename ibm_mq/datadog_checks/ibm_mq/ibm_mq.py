# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any

from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.ibm_mq.collectors.stats_collector import StatsCollector
from datadog_checks.ibm_mq.metrics import COUNT, GAUGE

from . import connection, errors
from .collectors import ChannelMetricCollector, QueueMetricCollector
from .config import IBMMQConfig

try:
    import pymqi
except ImportError as e:
    pymqiException = e
    pymqi = None


class IbmMqCheck(AgentCheck):
    SERVICE_CHECK = 'ibm_mq.can_connect'

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(IbmMqCheck, self).__init__(*args, **kwargs)
        self.config = IBMMQConfig(self.instance)

        if not pymqi:
            self.log.error("You need to install pymqi: %s", pymqiException)
            raise errors.PymqiException("You need to install pymqi: {}".format(pymqiException))

        self.queue_metric_collector = QueueMetricCollector(
            self.config, self.service_check, self.warning, self.send_metric, self.send_metrics_from_properties, self.log
        )
        self.channel_metric_collector = ChannelMetricCollector(self.config, self.service_check, self.gauge, self.log)
        self.stats_collector = StatsCollector(self.config, self.send_metrics_from_properties, self.log)

    def check(self, _):
        try:
            queue_manager = connection.get_queue_manager_connection(self.config)
            self.service_check(self.SERVICE_CHECK, AgentCheck.OK, self.config.tags)
        except Exception as e:
            self.warning("cannot connect to queue manager: %s", e)
            self.service_check(self.SERVICE_CHECK, AgentCheck.CRITICAL, self.config.tags)
            return

        try:
            self.channel_metric_collector.get_pcf_channel_metrics(queue_manager)
            self.queue_metric_collector.collect_queue_metrics(queue_manager)
            if self.config.collect_statistics_metrics:
                self.stats_collector.collect(queue_manager)
        finally:
            queue_manager.disconnect()

    def send_metric(self, metric_type, metric_name, metric_value, tags):
        if metric_type in [GAUGE, COUNT]:
            getattr(self, metric_type)(metric_name, metric_value, tags=tags)
        else:
            self.log.warning("Unknown metric type `%s` for metric `%s`", metric_type, metric_name)

    def send_metrics_from_properties(self, properties, metrics_map, prefix, tags):
        for metric_name, (pymqi_type, metric_type) in iteritems(metrics_map):
            metric_full_name = '{}.{}'.format(prefix, metric_name)
            if pymqi_type not in properties:
                self.log.debug("MQ type `%s` not found in properties for metric `%s` and tags `%s`", metric_name, tags)
                continue
            try:
                metric_value = int(properties[pymqi_type])
            except ValueError as e:
                self.log.debug(
                    "Cannot convert `%s` to int for metric `%s` ang tags `%s`: %s",
                    properties[pymqi_type],
                    metric_name,
                    tags,
                    e,
                )
                return
            self.send_metric(metric_type, metric_full_name, metric_value, tags)
