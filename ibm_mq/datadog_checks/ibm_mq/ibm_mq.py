# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.checks import AgentCheck

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

        try:
            self.queue_manager_stats(queue_manager, config.tags, metrics)

            for queue_name in config.queues:
                queue_tags = config.tags + ["queue:{}".format(queue_name)]
                try:
                    queue = pymqi.Queue(queue_manager, queue_name)
                    self.queue_stats(queue, queue_tags, metrics)
                    self.service_check(self.QUEUE_SERVICE_CHECK, AgentCheck.OK, queue_tags)
                    queue.close()
                except Exception as e:
                    self.warning('Cannot connect to queue {}: {}'.format(queue_name, e))
                    self.service_check(self.QUEUE_SERVICE_CHECK, AgentCheck.CRITICAL, queue_tags)
        finally:
            queue_manager.disconnect()

    def queue_manager_stats(self, queue_manager, tags, metrics):
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

    def queue_stats(self, queue, tags, metrics):
        """
        Grab stats from queues
        """
        for mname, pymqi_value in iteritems(metrics.queue_metrics()):
            try:
                mname = '{}.queue.{}'.format(self.METRIC_PREFIX, mname)
                m = queue.inquire(pymqi_value)
                self.gauge(mname, m, tags=tags)
            except pymqi.Error as e:
                self.warning("Error getting queue stats: {}".format(e))

        for mname, func in iteritems(metrics.queue_metrics_functions()):
            try:
                mname = '{}.queue.{}'.format(self.METRIC_PREFIX, mname)
                m = func(queue)
                self.gauge(mname, m, tags=tags)
            except pymqi.Error as e:
                self.warning("Error getting queue stats: {}".format(e))

        for mname, value_dict in iteritems(metrics.failure_prone_queue_metrics()):
            mname = '{}.queue.{}'.format(self.METRIC_PREFIX, mname)
            pymqi_value = value_dict['value']
            default_value = value_dict['value']
            try:
                m = queue.inquire(pymqi_value)
            except pymqi.Error as e:
                m = default_value
            self.gauge(mname, m, tags=tags)
