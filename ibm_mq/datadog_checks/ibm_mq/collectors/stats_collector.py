# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pymqi.CMQC import MQRC_NO_MSG_AVAILABLE
from pymqi.CMQCFC import (
    MQCMD_STATISTICS_CHANNEL,
    MQCMD_STATISTICS_MQI,
    MQCMD_STATISTICS_Q,
    MQGACF_CHL_STATISTICS_DATA,
    MQIAMO_MSGS,
)

from datadog_checks.base import AgentCheck
from datadog_checks.ibm_mq.collectors.utils import CustomPCFExecute

try:
    import pymqi
except ImportError as e:
    pymqiException = e
    pymqi = None

STATISTICS_QUEUE_NAME = 'SYSTEM.ADMIN.STATISTICS.QUEUE'


class StatsCollector(object):
    def __init__(self, check):
        # type: (AgentCheck) -> None
        self.check = check

    def collect(self, queue_manager):
        queue = pymqi.Queue(queue_manager, STATISTICS_QUEUE_NAME)
        self.check.log.debug("Start stats collection")

        try:
            while True:
                message = queue.get()
                message, header = CustomPCFExecute.unpack(message)

                if header.Command == MQCMD_STATISTICS_CHANNEL:
                    channels = message[MQGACF_CHL_STATISTICS_DATA]
                    self.check.log.info(
                        {
                            'type': 'MQCMD_STATISTICS_CHANNEL',
                            'MQGACF_CHL_STATISTICS_DATA': message[MQGACF_CHL_STATISTICS_DATA],
                        }
                    )
                    for channel in channels:
                        self.check.log.info({'MQIAMO_MSGS': channel[MQIAMO_MSGS]})
                        self.check.gauge('ibm_mq.stats.channel.msgs', channel[MQIAMO_MSGS])
                elif header.Command == MQCMD_STATISTICS_MQI:
                    self.check.log.debug('MQCMD_STATISTICS_MQI not implemented yet')
                elif header.Command == MQCMD_STATISTICS_Q:
                    self.check.log.debug('MQCMD_STATISTICS_Q not implemented yet')
                else:
                    self.check.log.debug('Unknown command: {}'.format(header.Command))
                if header.Control == pymqi.CMQCFC.MQCFC_LAST:
                    break
        except pymqi.MQMIError as err:
            if err.reason == MQRC_NO_MSG_AVAILABLE:
                pass
            else:
                raise
        finally:
            queue.close()
