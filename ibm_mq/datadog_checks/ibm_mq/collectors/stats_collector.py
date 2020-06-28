# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pymqi.CMQC import MQRC_NO_MSG_AVAILABLE
from pymqi.CMQCFC import (
    MQCACH_CHANNEL_NAME,
    MQCMD_STATISTICS_CHANNEL,
    MQCMD_STATISTICS_MQI,
    MQCMD_STATISTICS_Q,
    MQGACF_CHL_STATISTICS_DATA,
    MQIACH_CHANNEL_TYPE,
    MQIAMO_MSGS,
)

from datadog_checks.base import AgentCheck, to_native_string
from datadog_checks.ibm_mq.collectors.utils import CustomPCFExecute

try:
    import pymqi
    from pymqi import Queue
except ImportError as e:
    pymqiException = e
    pymqi = None

STATISTICS_QUEUE_NAME = 'SYSTEM.ADMIN.STATISTICS.QUEUE'


CHANNEL_TYPE_TO_STR = {
    pymqi.CMQC.MQCHT_SENDER: 'sender',
    pymqi.CMQC.MQCHT_SERVER: 'server',
    pymqi.CMQC.MQCHT_RECEIVER: 'receiver',
    pymqi.CMQC.MQCHT_REQUESTER: 'requester',
    pymqi.CMQC.MQCHT_CLUSRCVR: 'clusrcvr',
    pymqi.CMQC.MQCHT_CLUSSDR: 'clussdr',
}


def get_channel_type(raw_type):
    return CHANNEL_TYPE_TO_STR.get(raw_type, 'unknown')


class StatsCollector(object):
    def __init__(self, check):
        # type: (AgentCheck) -> None
        self.check = check

    def collect(self, queue_manager):
        queue = Queue(queue_manager, STATISTICS_QUEUE_NAME)
        self.check.log.debug("Start stats collection")

        try:
            while True:
                raw_message = queue.get()
                message, header = CustomPCFExecute.unpack(raw_message)

                if header.Command == MQCMD_STATISTICS_CHANNEL:
                    channels = message[MQGACF_CHL_STATISTICS_DATA]
                    self.check.log.info(
                        {
                            'type': 'MQCMD_STATISTICS_CHANNEL',
                            'MQGACF_CHL_STATISTICS_DATA': message[MQGACF_CHL_STATISTICS_DATA],
                        }
                    )
                    for channel_info in channels:
                        channel_name = to_native_string(channel_info[MQCACH_CHANNEL_NAME]).strip()
                        channel_type = get_channel_type(channel_info[MQIACH_CHANNEL_TYPE])
                        tags = [
                            'channel:{}'.format(channel_name),
                            'channel_type:{}'.format(channel_type),
                        ]
                        self.check.gauge('ibm_mq.stats.channel.msgs', channel_info[MQIAMO_MSGS], tags=tags)
                        self.check.gauge('ibm_mq.stats.channel.msgs2', channel_info[MQIAMO_MSGS], tags=tags)
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
