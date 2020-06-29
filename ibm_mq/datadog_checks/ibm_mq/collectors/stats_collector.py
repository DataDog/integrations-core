# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pymqi.CMQC import MQRC_NO_MSG_AVAILABLE
from pymqi.CMQCFC import MQCMD_STATISTICS_CHANNEL, MQCMD_STATISTICS_MQI, MQCMD_STATISTICS_Q
from six import iteritems

from datadog_checks.ibm_mq.collectors.utils import CustomPCFExecute
from datadog_checks.ibm_mq.stats_wrapper.queue_stats import QueueStats

from ..metrics import METRIC_PREFIX, channel_stats_metrics, queue_stats_metrics
from ..stats_wrapper import ChannelStats

try:
    import pymqi
    from pymqi import Queue
except ImportError as e:
    pymqiException = e
    pymqi = None


STATISTICS_QUEUE_NAME = 'SYSTEM.ADMIN.STATISTICS.QUEUE'


class StatsCollector(object):
    def __init__(self, config, gauge, log):
        self.config = config
        self.gauge = gauge
        self.log = log

    def collect(self, queue_manager):
        queue = Queue(queue_manager, STATISTICS_QUEUE_NAME)
        self.log.debug("Start stats collection")
        try:
            while True:
                # TODO: collect only from agent startup
                bin_message = queue.get()
                message, header = CustomPCFExecute.unpack(bin_message)
                if header.Command == MQCMD_STATISTICS_CHANNEL:
                    self.log.debug('collect channel stats')
                    self._collect_channel_stats(message)
                elif header.Command == MQCMD_STATISTICS_MQI:
                    self.log.debug('MQCMD_STATISTICS_MQI not implemented yet')
                elif header.Command == MQCMD_STATISTICS_Q:
                    self._collect_queue_stats(message)
                else:
                    self.log.debug('Unknown/NotImplemented command: %s', header.Command)
        except pymqi.MQMIError as err:
            if err.reason == MQRC_NO_MSG_AVAILABLE:
                pass
            else:
                raise
        finally:
            queue.close()

    def _collect_channel_stats(self, message):
        channel_stats = ChannelStats(message)
        self.log.debug('Collect channel stats. Number of channels: %s', len(channel_stats.channels))
        for channel_info in channel_stats.channels:
            tags = self.config.tags_no_channel + [
                'channel:{}'.format(channel_info.name),
                'channel_type:{}'.format(channel_info.type),
                'remote_q_mgr_name:{}'.format(channel_info.remote_q_mgr_name),
                'connection_name:{}'.format(channel_info.connection_name),
            ]
            prefix = '{}.stats.channel'.format(METRIC_PREFIX)
            metrics_map = channel_stats_metrics()
            self._submit_metrics_from_properties(prefix, channel_info.properties, metrics_map, tags)

    def _collect_queue_stats(self, message):
        queue_stats = QueueStats(message)
        self.log.debug('Collect queue stats. Number of queues: %s', len(queue_stats.queues))
        for queue_info in queue_stats.queues:
            tags = self.config.tags_no_channel + [
                'queue:{}'.format(queue_info.name),
                'queue_type:{}'.format(queue_info.type),
                'definition_type:{}'.format(queue_info.definition_type),
            ]
            prefix = '{}.stats.queue'.format(METRIC_PREFIX)
            metrics_map = queue_stats_metrics()
            self._submit_metrics_from_properties(prefix, queue_info.properties, metrics_map, tags)

    def _submit_metrics_from_properties(self, prefix, properties, metrics_map, tags):
        for metric_name, pymqi_type in iteritems(metrics_map):
            metric_full_name = '{}.{}'.format(prefix, metric_name)
            if pymqi_type not in properties:
                self.log.debug("metric not found: %s", metric_name)
                continue
            metric_value = int(properties[pymqi_type])
            self.gauge(metric_full_name, metric_value, tags=tags)
