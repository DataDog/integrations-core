# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging  # noqa: F401
from typing import Any, Callable, Dict, List, Set  # noqa: F401

from six import iteritems

from datadog_checks.base import AgentCheck, to_string
from datadog_checks.base.types import ServiceCheck  # noqa: F401
from datadog_checks.ibm_mq.metrics import GAUGE

from .. import metrics
from ..config import IBMMQConfig  # noqa: F401

try:
    import pymqi
except ImportError as e:
    pymqiException = e
    pymqi = None
else:
    # Since pymqi is not be available/installed on win/macOS when running e2e,
    # we load the following constants only pymqi import succeed
    SUPPORTED_QUEUE_TYPES = [pymqi.CMQC.MQQT_LOCAL, pymqi.CMQC.MQQT_MODEL]


class QueueMetricCollector(object):
    QUEUE_SERVICE_CHECK = 'ibm_mq.queue'
    QUEUE_MANAGER_SERVICE_CHECK = 'ibm_mq.queue_manager'

    def __init__(self, config, service_check, warning, send_metric, send_metrics_from_properties, log):
        # type: (IBMMQConfig, Callable, Callable, Callable, Callable, logging.LoggerAdapter) -> None
        self.config = config  # type: IBMMQConfig
        self.service_check = service_check  # type: Callable[[str, ServiceCheck, List[str]], None]
        self.warning = warning  # type: Callable
        self.send_metric = send_metric  # type: Callable[[str, str, Any, List[str]], None]
        self.send_metrics_from_properties = (
            send_metrics_from_properties
        )  # type: Callable[[Dict, Dict, str, List[str]], None]
        self.log = log  # type: logging.LoggerAdapter
        self.user_provided_queues = set(self.config.queues)  # type: Set[str]

    def collect_queue_metrics(self, queue_manager):
        queues = self.discover_queues(queue_manager)
        self.queue_manager_stats(queue_manager, self.config.tags)

        for queue_name in queues:
            queue_tags = self.config.tags + ["queue:{}".format(queue_name)]

            for regex, q_tags in self.config.queue_tag_re:
                if regex.match(queue_name):
                    queue_tags.extend(q_tags)

            try:
                self.queue_stats(queue_manager, queue_name, queue_tags)
                # some system queues don't have PCF metrics
                # so we don't collect those metrics from those queues
                if queue_name not in self.config.DISALLOWED_QUEUES:
                    self.get_pcf_queue_status_metrics(queue_manager, queue_name, queue_tags)

                    # if collect queue reset metrics is disabled, skip this
                    if self.config.collect_reset_queue_metrics:
                        self.get_pcf_queue_reset_metrics(queue_manager, queue_name, queue_tags)
                self.service_check(self.QUEUE_SERVICE_CHECK, AgentCheck.OK, queue_tags, hostname=self.config.hostname)
            except Exception as e:
                self.warning('Cannot connect to queue %s: %s', queue_name, e)
                self.service_check(
                    self.QUEUE_SERVICE_CHECK,
                    AgentCheck.CRITICAL,
                    queue_tags,
                    message=str(e),
                    hostname=self.config.hostname,
                )

    def discover_queues(self, queue_manager):
        # type: (pymqi.QueueManager) -> Set[str]
        discovered_queues = set()
        if self.config.auto_discover_queues and not self.config.queue_patterns or self.config.queue_regex:
            discovered_queues.update(self._discover_queues(queue_manager, '*'))

        if self.config.queue_patterns:
            for pattern in self.config.queue_patterns:
                discovered_queues.update(self._discover_queues(queue_manager, pattern))

        if self.config.queue_regex:
            keep_queues = set()
            for queue_pattern in self.config.queue_regex:
                for queue in discovered_queues:
                    if queue_pattern.match(queue):
                        keep_queues.add(queue)
            self.log.debug(
                "%s of the %s discovered queues match the queue_regex", len(keep_queues), len(discovered_queues)
            )
            discovered_queues = keep_queues

        discovered_queues.update(self.user_provided_queues)
        return discovered_queues

    def _discover_queues(self, queue_manager, mq_pattern_filter):
        # type: (pymqi.QueueManager, str) -> List[str]
        queues = []

        for queue_type in SUPPORTED_QUEUE_TYPES:
            args = {pymqi.CMQC.MQCA_Q_NAME: pymqi.ensure_bytes(mq_pattern_filter), pymqi.CMQC.MQIA_Q_TYPE: queue_type}
            pcf = None
            try:
                pcf = pymqi.PCFExecute(
                    queue_manager, response_wait_interval=self.config.timeout, convert=self.config.convert_endianness
                )
                response = pcf.MQCMD_INQUIRE_Q(args)
            except pymqi.MQMIError as e:
                # Don't warn if no messages, see:
                # https://github.com/dsuch/pymqi/blob/v1.12.0/docs/examples.rst#how-to-wait-for-multiple-messages
                if e.comp == pymqi.CMQC.MQCC_FAILED and e.reason == pymqi.CMQC.MQRC_NO_MSG_AVAILABLE:
                    self.log.debug("No queue info available")
                elif e.comp == pymqi.CMQC.MQCC_FAILED and e.reason == pymqi.CMQC.MQRC_UNKNOWN_OBJECT_NAME:
                    self.log.debug("No matching queue of type %d for pattern %s", queue_type, mq_pattern_filter)
                else:
                    self.warning("Error discovering queue: %s", e)
            else:
                for queue_info in response:
                    queue = queue_info.get(pymqi.CMQC.MQCA_Q_NAME, None)
                    if queue:
                        queue_name = to_string(queue).strip()
                        self.log.debug("Discovered queue: %s", queue_name)
                        queues.append(queue_name)
                    else:
                        self.log.debug('Discovered queue with empty name, skipping.')
                        continue
                self.log.debug("%s queues discovered", str(len(queues)))
            finally:
                # Close internal reply queue to prevent filling up a dead-letter queue.
                # https://github.com/dsuch/pymqi/blob/084ab0b2638f9d27303a2844badc76635c4ad6de/code/pymqi/__init__.py#L2892-L2902
                # https://dsuch.github.io/pymqi/examples.html#how-to-specify-dynamic-reply-to-queues
                if pcf is not None:
                    pcf.disconnect()

        if not queues:
            self.warning("No matching queue of type MQQT_LOCAL or MQQT_REMOTE for pattern %s", mq_pattern_filter)

        return queues

    def queue_manager_stats(self, queue_manager, tags):
        """
        Get stats from the queue manager
        """
        for mname, pymqi_value in iteritems(metrics.queue_manager_metrics()):
            try:
                m = queue_manager.inquire(pymqi_value)
                mname = '{}.queue_manager.{}'.format(metrics.METRIC_PREFIX, mname)
                self.send_metric(GAUGE, mname, m, tags=tags)
                self.service_check(self.QUEUE_MANAGER_SERVICE_CHECK, AgentCheck.OK, tags, hostname=self.config.hostname)
            except pymqi.Error as e:
                self.warning("Error getting queue manager stats: %s", e)
                self.service_check(
                    self.QUEUE_MANAGER_SERVICE_CHECK,
                    AgentCheck.CRITICAL,
                    tags,
                    message=str(e),
                    hostname=self.config.hostname,
                )

    def queue_stats(self, queue_manager, queue_name, tags):
        """
        Grab stats from queues
        """
        pcf = None
        try:
            args = {pymqi.CMQC.MQCA_Q_NAME: pymqi.ensure_bytes(queue_name), pymqi.CMQC.MQIA_Q_TYPE: pymqi.CMQC.MQQT_ALL}
            pcf = pymqi.PCFExecute(
                queue_manager, response_wait_interval=self.config.timeout, convert=self.config.convert_endianness
            )
            response = pcf.MQCMD_INQUIRE_Q(args)
        except pymqi.MQMIError as e:
            # Don't warn if no messages, see:
            # https://github.com/dsuch/pymqi/blob/v1.12.0/docs/examples.rst#how-to-wait-for-multiple-messages
            if e.comp == pymqi.CMQC.MQCC_FAILED and e.reason == pymqi.CMQC.MQRC_NO_MSG_AVAILABLE:
                self.log.debug("No stat messages available for queue %s", queue_name)
            else:
                self.warning("Error getting queue stats for %s: %s", queue_name, e)
        else:
            # Response is a list. It likely has only one member in it.
            for queue_info in response:
                self._submit_queue_stats(queue_info, queue_name, tags)
        finally:
            if pcf is not None:
                pcf.disconnect()

    def _submit_queue_stats(self, queue_info, queue_name, tags):
        for metric_suffix, mq_attr in iteritems(metrics.queue_metrics()):
            metric_name = '{}.queue.{}'.format(metrics.METRIC_PREFIX, metric_suffix)
            if callable(mq_attr):
                metric_value = mq_attr(queue_info)
                if metric_value is not None:
                    self.send_metric(GAUGE, metric_name, metric_value, tags=tags)
                else:
                    self.log.debug("Date for attribute %s not found for queue %s", metric_suffix, queue_name)
            else:
                if mq_attr in queue_info:
                    metric_value = queue_info[mq_attr]
                    self.send_metric(GAUGE, metric_name, metric_value, tags=tags)
                else:
                    self.log.debug("Attribute %s (%s) not found for queue %s", metric_suffix, mq_attr, queue_name)

    def get_pcf_queue_status_metrics(self, queue_manager, queue_name, tags):
        pcf = None
        try:
            args = {
                pymqi.CMQC.MQCA_Q_NAME: pymqi.ensure_bytes(queue_name),
                pymqi.CMQC.MQIA_Q_TYPE: pymqi.CMQC.MQQT_ALL,
                pymqi.CMQCFC.MQIACF_Q_STATUS_ATTRS: pymqi.CMQCFC.MQIACF_ALL,
            }
            pcf = pymqi.PCFExecute(
                queue_manager, response_wait_interval=self.config.timeout, convert=self.config.convert_endianness
            )
            response = pcf.MQCMD_INQUIRE_Q_STATUS(args)
        except pymqi.MQMIError as e:
            # Don't warn if no messages, see:
            # https://github.com/dsuch/pymqi/blob/v1.12.0/docs/examples.rst#how-to-wait-for-multiple-messages
            if e.comp == pymqi.CMQC.MQCC_FAILED and e.reason == pymqi.CMQC.MQRC_NO_MSG_AVAILABLE:
                self.log.debug("No PCF queue status messages available for queue %s", queue_name)
            else:
                self.warning("Error getting pcf queue status for %s: %s", queue_name, e)
        else:
            # Response is a list. It likely has only one member in it.
            for queue_info in response:
                for mname, values in iteritems(metrics.pcf_metrics()):
                    metric_name = '{}.queue.{}'.format(metrics.METRIC_PREFIX, mname)
                    try:
                        if callable(values):
                            metric_value = values(self.config.qm_timezone, queue_info)
                            if metric_value is not None:
                                self.send_metric(GAUGE, metric_name, metric_value, tags=tags)
                            else:
                                msg = """
                                    Unable to get %s. Turn on queue level monitoring to access these metrics for %s.
                                    Check `DISPLAY QSTATUS(%s) MONITOR`.
                                    """
                                self.log.debug(msg, metric_name, queue_name, queue_name)
                        else:
                            failure_value = values['failure']
                            pymqi_value = values['pymqi_value']
                            metric_value = int(queue_info.get(pymqi_value, None))

                            if metric_value > failure_value:
                                self.send_metric(GAUGE, metric_name, metric_value, tags=tags)
                            else:
                                msg = "Unable to get {}, turn on queue level monitoring to access these metrics for {}"
                                msg = msg.format(metric_name, queue_name)
                                self.log.debug(msg)
                    except Exception as e:
                        msg = "Unable to get metric {} from queue {}. Error is {}.".format(metric_name, queue_name, e)
                        self.log.warning(msg)
        finally:
            if pcf is not None:
                pcf.disconnect()

    def get_pcf_queue_reset_metrics(self, queue_manager, queue_name, tags):
        pcf = None
        try:
            args = {pymqi.CMQC.MQCA_Q_NAME: pymqi.ensure_bytes(queue_name)}
            pcf = pymqi.PCFExecute(
                queue_manager, response_wait_interval=self.config.timeout, convert=self.config.convert_endianness
            )
            response = pcf.MQCMD_RESET_Q_STATS(args)
        except pymqi.MQMIError as e:
            # Don't warn if no messages, see:
            # https://github.com/dsuch/pymqi/blob/v1.12.0/docs/examples.rst#how-to-wait-for-multiple-messages
            if e.comp == pymqi.CMQC.MQCC_FAILED and e.reason == pymqi.CMQC.MQRC_NO_MSG_AVAILABLE:
                self.log.debug("No PCF queue reset metrics messages available for queue %s", queue_name)
            else:
                self.warning("Error getting pcf queue reset metrics for %s: %s", queue_name, e)
        else:
            # Response is a list. It likely has only one member in it.
            for queue_info in response:
                metrics_map = metrics.pcf_status_reset_metrics()
                prefix = "{}.queue".format(metrics.METRIC_PREFIX)
                self.send_metrics_from_properties(queue_info, metrics_map, prefix, tags)
        finally:
            if pcf is not None:
                pcf.disconnect()
