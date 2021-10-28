# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pymqi.CMQCFC import MQCMD_STATISTICS_CHANNEL, MQCMD_STATISTICS_Q

from datadog_checks.ibm_mq.stats.base_stats import BaseStats
from datadog_checks.ibm_mq.stats.queue_stats import QueueStats

from ..metrics import METRIC_PREFIX, channel_stats_metrics, queue_stats_metrics
from ..stats import ChannelStats

try:
    import pymqi
    from pymqi import Queue
except ImportError as e:
    pymqiException = e
    pymqi = None


STATISTICS_QUEUE_NAME = 'SYSTEM.ADMIN.STATISTICS.QUEUE'
STATS_METRIC_CHANNEL_PREFIX = '{}.stats.channel'.format(METRIC_PREFIX)
STATS_METRIC_QUEUE_PREFIX = '{}.stats.queue'.format(METRIC_PREFIX)


class StatsCollector(object):
    def __init__(self, config, send_metrics_from_properties, log):
        self.config = config
        self.send_metrics_from_properties = send_metrics_from_properties
        self.log = log

    def collect(self, queue_manager):
        """
        Collect Statistics Messages

        Docs: https://www.ibm.com/support/knowledgecenter/SSFKSJ_9.1.0/com.ibm.mq.mon.doc/q037320_.htm
        """
        self.log.debug("Collecting stats newer than %s", self.config.instance_creation_datetime)
        queue = Queue(queue_manager, STATISTICS_QUEUE_NAME)

        try:
            # It's expected for the loop to stop when pymqi.MQMIError is raised with reason MQRC_NO_MSG_AVAILABLE.
            while True:
                bin_message = queue.get()
                self.log.trace('Stats binary message: %s', bin_message)

                message, header = pymqi.PCFExecute.unpack(bin_message)
                self.log.trace('Stats unpacked message: %s, Stats unpacked header: %s', message, header)

                stats = self._get_stats(message, header)

                # We only collect metrics generated after the check instance creation.
                if stats.start_datetime < self.config.instance_creation_datetime:
                    self.log.debug(
                        "Skipping messages created before agent startup. "
                        "Message time: %s / Check instance creation time: %s",
                        stats.start_datetime,
                        self.config.instance_creation_datetime,
                    )
                    continue

                if isinstance(stats, ChannelStats):
                    self._collect_channel_stats(stats)
                elif isinstance(stats, QueueStats):
                    self._collect_queue_stats(stats)
                else:
                    self.log.debug('Unknown/NotImplemented command: %s', header.Command)
        except pymqi.MQMIError as e:
            # Don't warn if no messages, see:
            # https://github.com/dsuch/pymqi/blob/v1.12.0/docs/examples.rst#how-to-wait-for-multiple-messages
            if e.comp == pymqi.CMQC.MQCC_FAILED and e.reason == pymqi.CMQC.MQRC_NO_MSG_AVAILABLE:
                self.log.debug("No messages available")
            else:
                raise
        finally:
            try:
                queue.close()
            except pymqi.PYIFError as e:
                self.log.debug("Could not close queue: %s", str(e))

    def _collect_channel_stats(self, channel_stats):
        self.log.debug('Collect channel stats. Number of channels: %s', len(channel_stats.channels))
        for channel_info in channel_stats.channels:
            tags = self.config.tags_no_channel + [
                'channel:{}'.format(channel_info.name),
                'channel_type:{}'.format(channel_info.type),
                'remote_q_mgr_name:{}'.format(channel_info.remote_q_mgr_name),
                'connection_name:{}'.format(channel_info.connection_name),
            ]
            metrics_map = channel_stats_metrics()
            self.send_metrics_from_properties(
                channel_info.properties, metrics_map=metrics_map, prefix=STATS_METRIC_CHANNEL_PREFIX, tags=tags
            )

    def _collect_queue_stats(self, queue_stats):
        self.log.debug('Collect queue stats. Number of queues: %s', len(queue_stats.queues))
        for queue_info in queue_stats.queues:
            tags = self.config.tags_no_channel + [
                'queue:{}'.format(queue_info.name),
                'queue_type:{}'.format(queue_info.type),
                'definition_type:{}'.format(queue_info.definition_type),
            ]
            metrics_map = queue_stats_metrics()
            self.send_metrics_from_properties(
                queue_info.properties, metrics_map=metrics_map, prefix=STATS_METRIC_QUEUE_PREFIX, tags=tags
            )

    @staticmethod
    def _get_stats(message, header):
        if header.Command == MQCMD_STATISTICS_CHANNEL:
            stats = ChannelStats(message)
        elif header.Command == MQCMD_STATISTICS_Q:
            stats = QueueStats(message)
        else:
            stats = BaseStats(message)
        return stats
