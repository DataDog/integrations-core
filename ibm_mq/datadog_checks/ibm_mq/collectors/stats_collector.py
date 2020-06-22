# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pymqi.CMQC import MQCA_Q_MGR_NAME
from pymqi.CMQCFC import MQCMD_STATISTICS_CHANNEL, MQCMD_STATISTICS_MQI, MQCMD_STATISTICS_Q

from datadog_checks.base import AgentCheck
from datadog_checks.ibm_mq.collectors.utils import unpack_header

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
        message = queue.get()
        # self.check.log.info("RECEIVED MSG: %s", message)

        unpacked, control = pymqi.PCFExecute.unpack(message)

        # self.check.log.info("UNPACKED MSG: %s", unpacked)

        header = unpack_header(message)
        # self.check.log.info("UNPACKED HEADER: %s", header)

        if header.Command == MQCMD_STATISTICS_CHANNEL:
            self.check.log.info({
                'type': 'MQCMD_STATISTICS_CHANNEL',
                # 'mgr name': unpacked[MQCA_Q_MGR_NAME],
            })
        elif header.Command == MQCMD_STATISTICS_MQI:
            self.check.log.info({
                'type': 'MQCMD_STATISTICS_MQI',
                # 'mgr name': unpacked[MQCA_Q_MGR_NAME],
            })
        elif header.Command == MQCMD_STATISTICS_Q:
            self.check.log.info({
                'type': 'MQCMD_STATISTICS_Q',
                # 'mgr name': unpacked[MQCA_Q_MGR_NAME],
            })

        queue.close()
