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


class StatsCollector(object):
    def __init__(self, check):
        # type: (AgentCheck) -> None
        self.check = check

    def collect(self, queue_manager):
        queue_name = 'SYSTEM.ADMIN.STATISTICS.QUEUE'
        queue = pymqi.Queue(queue_manager, queue_name)
        try:
            while True:
                # https://github.com/dsuch/pymqi/blob/0995dfb80c92646421bd4abb0f7f8a0d39fe0a08/code/tests/test_pcf.py#L183-L187
                message = queue.get()
                # self.check.log.info("RECEIVED MSG: %s", message)
                # self.check.log.info("UNPACKED MSG: %s", unpacked)
                # self.check.log.info("UNPACKED HEADER: %s", header)
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
                    self.check.log.info(
                        {
                            'type': 'MQCMD_STATISTICS_MQI',
                            # 'mgr name': unpacked[MQCA_Q_MGR_NAME],
                        }
                    )
                elif header.Command == MQCMD_STATISTICS_Q:
                    self.check.log.info(
                        {
                            'type': 'MQCMD_STATISTICS_Q',
                            # 'mgr name': unpacked[MQCA_Q_MGR_NAME],
                        }
                    )
        except pymqi.MQMIError as err:
            self.check.log.info(err)
            if err.reason == MQRC_NO_MSG_AVAILABLE:
                pass
            else:
                raise
        finally:
            queue.close()
