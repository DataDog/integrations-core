# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.checks import AgentCheck

from datadog_checks.base import ensure_bytes

from six import iteritems
import logging

from . import errors, metrics, connection
from .config import IBMMQConfig

try:
    import pymqi
except ImportError as e:
    pymqiException = e
    pymqi = None

log = logging.getLogger(__file__)


class IbmMqCheck(AgentCheck):

    METRIC_PREFIX = 'ibm_mq'

    SERVICE_CHECK = 'ibm_mq.can_connect'

    QUEUE_MANAGER_SERVICE_CHECK = 'ibm_mq.queue_manager'
    QUEUE_SERVICE_CHECK = 'ibm_mq.queue'

    CHANNEL_SERVICE_CHECK = 'ibm_mq.channel'

    def check(self, instance):
        config = IBMMQConfig(instance)
        config.check_properly_configured()

        if not pymqi:
            log.error("You need to install pymqi: {}".format(pymqiException))
            raise errors.PymqiException("You need to install pymqi: {}".format(pymqiException))

        try:
            queue_manager = connection.get_queue_manager_connection(config)
            self.service_check(self.SERVICE_CHECK, AgentCheck.OK, config.tags)
        except Exception as e:
            self.warning("cannot connect to queue manager: {}".format(e))
            self.service_check(self.SERVICE_CHECK, AgentCheck.CRITICAL, config.tags)
            return

        self.get_pcf_channel_metrics(queue_manager, config.tags, config)

        self.discover_queues(queue_manager, config)

        try:
            self.queue_manager_stats(queue_manager, config.tags)

            for queue_name in config.queues:
                queue_tags = config.tags + ["queue:{}".format(queue_name)]
                try:
                    queue = pymqi.Queue(queue_manager, queue_name)
                    self.queue_stats(queue, queue_tags)
                    # some system queues don't have PCF metrics
                    # so we don't collect those metrics from those queues
                    if queue_name not in config.DISALLOWED_QUEUES:
                        self.get_pcf_queue_metrics(queue_manager, queue_name, queue_tags)
                    self.service_check(self.QUEUE_SERVICE_CHECK, AgentCheck.OK, queue_tags)
                    queue.close()
                except Exception as e:
                    self.warning('Cannot connect to queue {}: {}'.format(queue_name, e))
                    self.service_check(self.QUEUE_SERVICE_CHECK, AgentCheck.CRITICAL, queue_tags)
        finally:
            queue_manager.disconnect()

    def discover_queues(self, queue_manager, config):
        queues = []
        if config.auto_discover_queues:
            queues.extend(self._discover_queues(queue_manager, '*'))

        if len(config.queue_patterns) > 0:
            for regex in config.queue_patterns:
                queues.extend(self._discover_queues(queue_manager, regex))

        config.add_queues(queues)

    def _discover_queues(self, queue_manager, regex):
        args = {
            pymqi.CMQC.MQCA_Q_NAME: ensure_bytes(regex),
            pymqi.CMQC.MQIA_Q_TYPE: pymqi.CMQC.MQQT_MODEL
        }
        queues = []

        try:
            pcf = pymqi.PCFExecute(queue_manager)
            response = pcf.MQCMD_INQUIRE_Q(args)
        except pymqi.MQMIError as e:
            self.warning("Error getting queue stats: {}".format(e))
        else:
            for queue_info in response:
                queue = queue_info[pymqi.CMQC.MQCA_Q_NAME]
                queue = queue.strip()
                queues.append(queue)

        return queues

    def queue_manager_stats(self, queue_manager, tags):
        """
        Get stats from the queue manager
        """
        for mname, pymqi_value in iteritems(metrics.queue_manager_metrics()):
            try:
                m = queue_manager.inquire(pymqi_value)

                mname = '{}.queue_manager.{}'.format(self.METRIC_PREFIX, mname)
                self.gauge(mname, m, tags=tags)
                self.service_check(self.QUEUE_MANAGER_SERVICE_CHECK, AgentCheck.OK, tags)
            except pymqi.Error as e:
                self.warning("Error getting queue manager stats: {}".format(e))
                self.service_check(self.QUEUE_MANAGER_SERVICE_CHECK, AgentCheck.CRITICAL, tags)

    def queue_stats(self, queue, tags):
        """
        Grab stats from queues
        """
        for mname, pymqi_value in iteritems(metrics.queue_metrics()):
            try:
                mname = '{}.queue.{}'.format(self.METRIC_PREFIX, mname)
                m = queue.inquire(pymqi_value)
                self.gauge(mname, m, tags=tags)
            except pymqi.Error as e:
                self.warning("Error getting queue stats for {}: {}".format(queue, e))

        for mname, func in iteritems(metrics.queue_metrics_functions()):
            try:
                mname = '{}.queue.{}'.format(self.METRIC_PREFIX, mname)
                m = func(queue)
                self.gauge(mname, m, tags=tags)
            except pymqi.Error as e:
                self.warning("Error getting queue stats for {}: {}".format(queue, e))

    def get_pcf_queue_metrics(self, queue_manager, queue_name, tags):
        try:
            args = {
                pymqi.CMQC.MQCA_Q_NAME: ensure_bytes(queue_name),
                pymqi.CMQC.MQIA_Q_TYPE: pymqi.CMQC.MQQT_MODEL,
                pymqi.CMQCFC.MQIACF_Q_STATUS_ATTRS: pymqi.CMQCFC.MQIACF_ALL,
            }
            pcf = pymqi.PCFExecute(queue_manager)
            response = pcf.MQCMD_INQUIRE_Q_STATUS(args)
        except pymqi.MQMIError as e:
            self.warning("Error getting queue stats for {}: {}".format(queue_name, e))
        else:
            # Response is a list. It likely has only one member in it.
            for queue_info in response:
                for mname, values in iteritems(metrics.pcf_metrics()):
                    failure_value = values['failure']
                    pymqi_value = values['pymqi_value']
                    mname = '{}.queue.{}'.format(self.METRIC_PREFIX, mname)
                    m = int(queue_info[pymqi_value])

                    if m > failure_value:
                        self.gauge(mname, m, tags=tags)
                    else:
                        msg = "Unable to get {}, turn on queue level monitoring to access these metrics for {}"
                        msg = msg.format(mname, queue_name)
                        log.debug(msg)

    def get_pcf_channel_metrics(self, queue_manager, tags, config):
        args = {
            pymqi.CMQCFC.MQCACH_CHANNEL_NAME: ensure_bytes('*')
        }

        try:
            pcf = pymqi.PCFExecute(queue_manager)
            response = pcf.MQCMD_INQUIRE_CHANNEL(args)
        except pymqi.MQMIError as e:
            self.log.warning("Error getting CHANNEL stats {}".format(e))
        else:
            channels = len(response)
            mname = '{}.channel.channels'.format(self.METRIC_PREFIX)
            self.gauge(mname, channels, tags=tags)

        # grab all the discoverable channels
        self._get_channel_status(queue_manager, '*', tags, config)

        # check specific channels as well
        # if a channel is not listed in the above one, a user may want to check it specifically,
        # in this case it'll fail
        for channel in config.channels:
            self._get_channel_status(queue_manager, channel, tags, config)

    def _get_channel_status(self, queue_manager, channel, tags, config):
        channel_tags = tags + ["channel:{}".format(channel)]
        try:
            args = {
                pymqi.CMQCFC.MQCACH_CHANNEL_NAME: ensure_bytes(channel)
            }
            pcf = pymqi.PCFExecute(queue_manager)
            response = pcf.MQCMD_INQUIRE_CHANNEL_STATUS(args)
        except pymqi.MQMIError as e:
            self.log.warning("Error getting CHANNEL stats {}".format(e))
            self.service_check(self.CHANNEL_SERVICE_CHECK, AgentCheck.CRITICAL, channel_tags)
        else:
            for channel_info in response:
                name = channel_info[pymqi.CMQCFC.MQCACH_CHANNEL_NAME]
                name = name.strip()

                # running = 3, stopped = 4
                status = channel_info[pymqi.CMQCFC.MQIACH_CHANNEL_STATUS]
                if status == 3:
                    self.service_check(self.CHANNEL_SERVICE_CHECK, AgentCheck.OK, channel_tags)
                elif status == 4:
                    self.service_check(self.CHANNEL_SERVICE_CHECK, AgentCheck.WARNING, channel_tags)
