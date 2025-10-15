# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pymqi.CMQC import MQCA_Q_NAME, MQIA_DEFINITION_TYPE, MQIA_Q_TYPE
from pymqi.CMQCFC import MQGACF_Q_STATISTICS_DATA

from datadog_checks.ibm_mq.stats.base_stats import BaseStats
from datadog_checks.ibm_mq.utils import sanitize_strings

try:
    import pymqi
except ImportError as e:
    pymqiException = e
    pymqi = None


QUEUE_TYPE_TO_STR = {
    pymqi.CMQC.MQQT_ALL: 'all',
    pymqi.CMQC.MQQT_LOCAL: 'local',
    pymqi.CMQC.MQQT_ALIAS: 'alias',
    pymqi.CMQC.MQQT_REMOTE: 'remote',
    pymqi.CMQC.MQQT_MODEL: 'model',
}


QUEUE_DEFINITION_TYPE_TO_STR = {
    pymqi.CMQC.MQQDT_PREDEFINED: 'predefined',
    pymqi.CMQC.MQQDT_PERMANENT_DYNAMIC: 'permanent_dynamic',
    pymqi.CMQC.MQQDT_TEMPORARY_DYNAMIC: 'temporary_dynamic',
}


def get_queue_type(raw_type):
    return QUEUE_TYPE_TO_STR.get(raw_type, 'unknown')


def get_queue_def_type(raw_type):
    return QUEUE_DEFINITION_TYPE_TO_STR.get(raw_type, 'unknown')


class QueueInfo(object):
    def __init__(self, raw_properties):
        self.name = sanitize_strings(raw_properties[MQCA_Q_NAME])
        self.type = get_queue_type(raw_properties[MQIA_Q_TYPE])
        self.definition_type = get_queue_def_type(raw_properties[MQIA_DEFINITION_TYPE])
        self.properties = raw_properties


class QueueStats(BaseStats):
    def __init__(self, raw_message, timezone=None):
        super(QueueStats, self).__init__(raw_message, timezone=timezone)
        self.queues = [QueueInfo(channel) for channel in raw_message[MQGACF_Q_STATISTICS_DATA]]
