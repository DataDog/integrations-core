from pymqi.CMQCFC import MQCACH_CHANNEL_NAME, MQGACF_CHL_STATISTICS_DATA, MQIACH_CHANNEL_TYPE, MQIAMO_MSGS

from datadog_checks.base import to_native_string

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
    def __init__(self, raw_channel_info):
        self.name = to_native_string(raw_channel_info[MQCACH_CHANNEL_NAME]).strip()
        self.type = get_channel_type(raw_channel_info[MQIACH_CHANNEL_TYPE])
        self.msgs = raw_channel_info[MQIAMO_MSGS]


class ChannelStats(object):
    def __init__(self, raw_message):
        self.channels = [ChannelInfo(channel) for channel in raw_message[MQGACF_CHL_STATISTICS_DATA]]
