# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pymqi.CMQC import MQCA_REMOTE_Q_MGR_NAME
from pymqi.CMQCFC import MQCACH_CHANNEL_NAME, MQCACH_CONNECTION_NAME, MQGACF_CHL_STATISTICS_DATA, MQIACH_CHANNEL_TYPE

from datadog_checks.ibm_mq.stats.base_stats import BaseStats
from datadog_checks.ibm_mq.utils import sanitize_strings

try:
    import pymqi
except ImportError as e:
    pymqiException = e
    pymqi = None

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


class ChannelInfo(object):
    def __init__(self, raw_properties):
        self.name = sanitize_strings(raw_properties[MQCACH_CHANNEL_NAME])
        self.type = get_channel_type(raw_properties[MQIACH_CHANNEL_TYPE])
        self.remote_q_mgr_name = sanitize_strings(raw_properties[MQCA_REMOTE_Q_MGR_NAME])
        self.connection_name = sanitize_strings(raw_properties[MQCACH_CONNECTION_NAME])
        self.properties = raw_properties


class ChannelStats(BaseStats):
    def __init__(self, raw_message, timezone=None):
        super(ChannelStats, self).__init__(raw_message, timezone=timezone)
        self.channels = [ChannelInfo(channel) for channel in raw_message[MQGACF_CHL_STATISTICS_DATA]]
