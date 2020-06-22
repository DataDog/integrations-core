# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import AgentCheck

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
        get_opts = pymqi.GMO(
            Options=pymqi.CMQC.MQGMO_NO_SYNCPOINT + pymqi.CMQC.MQGMO_FAIL_IF_QUIESCING,
            Version=pymqi.CMQC.MQGMO_VERSION_2,
            MatchOptions=pymqi.CMQC.MQMO_MATCH_CORREL_ID)

        queue_name = 'SYSTEM.ADMIN.STATISTICS.QUEUE'
        queue = pymqi.Queue(queue_manager, queue_name)
        message = queue.get()
        self.check.log.info("message", message)
        queue.close()
