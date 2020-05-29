# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from six import iteritems

from datadog_checks.base import AgentCheck, ensure_bytes, ensure_unicode
from datadog_checks.ibm_mq.metrics import GAUGE

from . import metrics

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

    def __init__(self, config, service_check, warning, send_metric, log):
        self.config = config
        self.service_check = service_check
        self.warning = warning
        self.send_metric = send_metric
        self.log = log
        self.queues = set(self.config.queues)

    def collect_queue_metrics(self, queue_manager):
        self.discover_queues(queue_manager)
        self.queue_manager_stats(queue_manager, self.config.tags)

        for queue_name in self.queues:
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
                    self.get_pcf_queue_reset_metrics(queue_manager, queue_name, queue_tags)
                self.service_check(self.QUEUE_SERVICE_CHECK, AgentCheck.OK, queue_tags)
            except Exception as e:
                self.warning('Cannot connect to queue %s: %s', queue_name, e)
                self.service_check(self.QUEUE_SERVICE_CHECK, AgentCheck.CRITICAL, queue_tags)

    def discover_queues(self, queue_manager):
        queues = []
        if self.config.auto_discover_queues:
            queues.extend(self._discover_queues(queue_manager, '*'))

        if self.config.queue_patterns:
            for pattern in self.config.queue_patterns:
                queues.extend(self._discover_queues(queue_manager, pattern))

        if self.config.queue_regex:
            if not queues:
                queues = self._discover_queues(queue_manager, '*')
            keep_queues = []
            for queue_pattern in self.config.queue_regex:
                for queue in queues:
                    if queue_pattern.match(queue):
                        keep_queues.append(queue)
            queues = keep_queues

        self.queues.update(queues)

    def _discover_queues(self, queue_manager, mq_pattern_filter):
        queues = []

        for queue_type in SUPPORTED_QUEUE_TYPES:
            args = {pymqi.CMQC.MQCA_Q_NAME: ensure_bytes(mq_pattern_filter), pymqi.CMQC.MQIA_Q_TYPE: queue_type}
            try:
                pcf = pymqi.PCFExecute(queue_manager)
                response = pcf.MQCMD_INQUIRE_Q(args)
            except pymqi.MQMIError as e:
                self.warning("Error discovering queue: %s", e)
            else:
                for queue_info in response:
                    queue = queue_info[pymqi.CMQC.MQCA_Q_NAME]
                    queues.append(ensure_unicode(queue).strip())

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
                self.service_check(self.QUEUE_MANAGER_SERVICE_CHECK, AgentCheck.OK, tags)
            except pymqi.Error as e:
                self.warning("Error getting queue manager stats: %s", e)
                self.service_check(self.QUEUE_MANAGER_SERVICE_CHECK, AgentCheck.CRITICAL, tags)

    def queue_stats(self, queue_manager, queue_name, tags):
        """
        Grab stats from queues
        """
        try:
            args = {pymqi.CMQC.MQCA_Q_NAME: ensure_bytes(queue_name), pymqi.CMQC.MQIA_Q_TYPE: pymqi.CMQC.MQQT_ALL}
            pcf = pymqi.PCFExecute(queue_manager)
            response = pcf.MQCMD_INQUIRE_Q(args)
        except pymqi.MQMIError as e:
            self.warning("Error getting queue stats for %s: %s", queue_name, e)
        else:
            # Response is a list. It likely has only one member in it.
            for queue_info in response:
                self._submit_queue_stats(queue_info, queue_name, tags)

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
        try:
            args = {
                pymqi.CMQC.MQCA_Q_NAME: ensure_bytes(queue_name),
                pymqi.CMQC.MQIA_Q_TYPE: pymqi.CMQC.MQQT_ALL,
                pymqi.CMQCFC.MQIACF_Q_STATUS_ATTRS: pymqi.CMQCFC.MQIACF_ALL,
            }
            pcf = pymqi.PCFExecute(queue_manager)
            response = pcf.MQCMD_INQUIRE_Q_STATUS(args)
        except pymqi.MQMIError as e:
            self.warning("Error getting pcf queue stats for %s: %s", queue_name, e)
        else:
            # Response is a list. It likely has only one member in it.
            for queue_info in response:
                for mname, values in iteritems(metrics.pcf_metrics()):
                    failure_value = values['failure']
                    pymqi_value = values['pymqi_value']
                    mname = '{}.queue.{}'.format(metrics.METRIC_PREFIX, mname)
                    m = int(queue_info[pymqi_value])

                    if m > failure_value:
                        self.send_metric(GAUGE, mname, m, tags=tags)
                    else:
                        msg = "Unable to get {}, turn on queue level monitoring to access these metrics for {}"
                        msg = msg.format(mname, queue_name)
                        self.log.debug(msg)

    def get_pcf_queue_reset_metrics(self, queue_manager, queue_name, tags):
        try:
            args = {pymqi.CMQC.MQCA_Q_NAME: ensure_bytes(queue_name)}
            pcf = pymqi.PCFExecute(queue_manager)
            response = pcf.MQCMD_RESET_Q_STATS(args)
        except pymqi.MQMIError as e:
            self.warning("Error getting pcf queue stats for %s: %s", queue_name, e)
        else:
            # Response is a list. It likely has only one member in it.
            for queue_info in response:
                for metric_name, (pymqi_type, metric_type) in iteritems(metrics.pcf_status_reset_metrics()):
                    metric_full_name = '{}.queue.{}'.format(metrics.METRIC_PREFIX, metric_name)
                    metric_value = int(queue_info[pymqi_type])
                    self.send_metric(metric_type, metric_full_name, metric_value, tags)
