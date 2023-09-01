# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading

from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.ibm_mq.collectors.stats_collector import StatsCollector
from datadog_checks.ibm_mq.metrics import COUNT, GAUGE

from . import connection, errors
from .collectors import ChannelMetricCollector, MetadataCollector, QueueMetricCollector
from .config import IBMMQConfig
from .process_matcher import QueueManagerProcessMatcher

try:
    from typing import Any, Dict, List  # noqa: F401
except ImportError:
    pass

try:
    import pymqi
except ImportError as e:
    pymqiException = e
    pymqi = None


class IbmMqCheck(AgentCheck):
    MATCHER_CREATION_LOCK = threading.Lock()
    process_matcher = None

    SERVICE_CHECK = 'ibm_mq.can_connect'

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(IbmMqCheck, self).__init__(*args, **kwargs)

        if not pymqi:
            self.log.error("You need to install pymqi: %s", pymqiException)
            raise errors.PymqiException("You need to install pymqi: {}".format(pymqiException))

        self._config = IBMMQConfig(self.instance, self.init_config)

        self.queue_metric_collector = QueueMetricCollector(
            self._config,
            self.service_check,
            self.warning,
            self.send_metric,
            self.send_metrics_from_properties,
            self.log,
        )
        self.channel_metric_collector = ChannelMetricCollector(self._config, self.service_check, self.gauge, self.log)
        self.metadata_collector = MetadataCollector(self._config, self.log)
        self.stats_collector = StatsCollector(self._config, self.send_metrics_from_properties, self.log)

        self.check_initializations.append(self.create_process_matcher)

    def check(self, _):
        if not self.check_queue_manager_process():
            message = 'Process not found, skipping check run'
            self.log.info(message)
            for sc_name in (self.SERVICE_CHECK, QueueMetricCollector.QUEUE_MANAGER_SERVICE_CHECK):
                self.service_check(
                    sc_name, self.UNKNOWN, self._config.tags, message=message, hostname=self._config.hostname
                )

            return

        try:
            queue_manager = connection.get_queue_manager_connection(self._config, self.log)
            self.service_check(self.SERVICE_CHECK, AgentCheck.OK, self._config.tags, hostname=self._config.hostname)
        except Exception as e:
            message = 'cannot connect to queue manager: {}'.format(e)
            self.warning(message)
            self.service_check(
                self.SERVICE_CHECK,
                AgentCheck.CRITICAL,
                self._config.tags,
                message=message,
                hostname=self._config.hostname,
            )
            self.service_check(
                QueueMetricCollector.QUEUE_MANAGER_SERVICE_CHECK,
                AgentCheck.CRITICAL,
                self._config.tags,
                message=message,
                hostname=self._config.hostname,
            )
            self.reset_queue_manager_process_match()
            raise

        self._collect_metadata(queue_manager)

        try:
            self.channel_metric_collector.get_pcf_channel_metrics(queue_manager)
            self.queue_metric_collector.collect_queue_metrics(queue_manager)
            if self._config.collect_statistics_metrics:
                self.stats_collector.collect(queue_manager)
        finally:
            queue_manager.disconnect()

    def send_metric(self, metric_type, metric_name, metric_value, tags):
        if metric_type in [GAUGE, COUNT]:
            getattr(self, metric_type)(metric_name, metric_value, tags=tags, hostname=self._config.hostname)
        else:
            self.log.warning("Unknown metric type `%s` for metric `%s`", metric_type, metric_name)

    @AgentCheck.metadata_entrypoint
    def _collect_metadata(self, queue_manager):
        try:
            version = self.metadata_collector.collect_metadata(queue_manager)
            if version:
                raw_version = '{}.{}.{}.{}'.format(version["major"], version["minor"], version["mod"], version["fix"])
                self.set_metadata('version', raw_version, scheme='parts', part_map=version)
                self.log.debug('Found ibm_mq version: %s', raw_version)
            else:
                self.log.debug('Could not retrieve ibm_mq version info')
        except Exception as e:
            self.log.debug('Could not retrieve ibm_mq version info: %s', e)

    def send_metrics_from_properties(self, properties, metrics_map, prefix, tags):
        # type: (Dict, Dict, str, List[str]) -> None
        for metric_name, (pymqi_type, metric_type) in iteritems(metrics_map):
            metric_full_name = '{}.{}'.format(prefix, metric_name)
            if pymqi_type not in properties:
                self.log.debug("MQ type `%s` not found in properties for metric `%s` and tags `%s`", metric_name, tags)
                continue

            values_to_submit = []
            value = properties[pymqi_type]

            if isinstance(value, list):
                # Some metrics are returned as a list of two values.
                # Index 0 = Contains the value for non-persistent messages
                # Index 1 = Contains the value for persistent messages
                # https://www.ibm.com/support/knowledgecenter/en/SSFKSJ_7.5.0/com.ibm.mq.mon.doc/q037510_.htm#q037510___q037510_2
                values_to_submit.append((tags + ['persistent:false'], value[0]))
                values_to_submit.append((tags + ['persistent:true'], value[1]))
            else:
                values_to_submit.append((tags, value))

            for new_tags, metric_value in values_to_submit:
                try:
                    metric_value = int(metric_value)
                except ValueError as e:
                    self.log.debug(
                        "Cannot convert `%s` to int for metric `%s` ang tags `%s`: %s",
                        properties[pymqi_type],
                        metric_name,
                        new_tags,
                        e,
                    )
                    return
                self.send_metric(metric_type, metric_full_name, metric_value, new_tags)

    def check_queue_manager_process(self):
        if self._config.queue_manager_process_pattern is None:
            return True

        return self.process_matcher.check_condition(self.check_id, self._config.queue_manager_process_pattern, self.log)

    def reset_queue_manager_process_match(self):
        if self._config.queue_manager_process_pattern is not None:
            self.log.debug('Resetting queue manager process match')
            return self.process_matcher.remove(self.check_id)

    def create_process_matcher(self):
        if self._config.queue_manager_process_pattern is not None:
            with IbmMqCheck.MATCHER_CREATION_LOCK:
                if IbmMqCheck.process_matcher is None:
                    limit = int(self.init_config.get('queue_manager_process_limit', 1))
                    IbmMqCheck.process_matcher = QueueManagerProcessMatcher(limit)

    def cancel(self):
        # This method is called when the check in unscheduled by the Agent.
        self.reset_queue_manager_process_match()
