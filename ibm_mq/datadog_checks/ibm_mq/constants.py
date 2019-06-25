# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import division

import datetime

from datadog_checks.base import AgentCheck, ensure_unicode

try:
    import pymqi
except ImportError:
    pymqi = None

METRIC_PREFIX = 'ibm_mq'

SUPPORTED_QUEUE_TYPES = [pymqi.CMQC.MQQT_LOCAL, pymqi.CMQC.MQQT_MODEL]

STATUS_MQCHS_UNKNOWN = -1

CHANNEL_STATUS_MAP = {
    pymqi.CMQCFC.MQCHS_INACTIVE: "inactive",
    pymqi.CMQCFC.MQCHS_BINDING: "binding",
    pymqi.CMQCFC.MQCHS_STARTING: "starting",
    pymqi.CMQCFC.MQCHS_RUNNING: "running",
    pymqi.CMQCFC.MQCHS_STOPPING: "stopping",
    pymqi.CMQCFC.MQCHS_RETRYING: "retrying",
    pymqi.CMQCFC.MQCHS_STOPPED: "stopped",
    pymqi.CMQCFC.MQCHS_REQUESTING: "requesting",
    pymqi.CMQCFC.MQCHS_PAUSED: "paused",
    pymqi.CMQCFC.MQCHS_INITIALIZING: "initializing",
    STATUS_MQCHS_UNKNOWN: "unknown",
}

SERVICE_CHECK_MAP = {
    pymqi.CMQCFC.MQCHS_INACTIVE: AgentCheck.CRITICAL,
    pymqi.CMQCFC.MQCHS_BINDING: AgentCheck.WARNING,
    pymqi.CMQCFC.MQCHS_STARTING: AgentCheck.WARNING,
    pymqi.CMQCFC.MQCHS_RUNNING: AgentCheck.OK,
    pymqi.CMQCFC.MQCHS_STOPPING: AgentCheck.CRITICAL,
    pymqi.CMQCFC.MQCHS_RETRYING: AgentCheck.WARNING,
    pymqi.CMQCFC.MQCHS_STOPPED: AgentCheck.CRITICAL,
    pymqi.CMQCFC.MQCHS_REQUESTING: AgentCheck.WARNING,
    pymqi.CMQCFC.MQCHS_PAUSED: AgentCheck.WARNING,
    pymqi.CMQCFC.MQCHS_INITIALIZING: AgentCheck.WARNING,
}


# Metric types
GAUGE = 'gauge'
RATE = 'rate'

# Service checks
SYSTEM_CAN_CONNECT_SERVICE_CHECK = 'ibm_mq.can_connect'
QUEUE_MANAGER_SERVICE_CHECK = 'ibm_mq.queue_manager'
CHANNEL_SERVICE_CHECK = 'ibm_mq.channel'
CHANNEL_STATUS_SERVICE_CHECK = 'ibm_mq.channel.status'
QUEUE_SERVICE_CHECK = 'ibm_mq.queue'

# Metric functions


def _depth_percent(queue_info):
    if pymqi.CMQC.MQIA_CURRENT_Q_DEPTH not in queue_info or pymqi.CMQC.MQIA_MAX_Q_DEPTH not in queue_info:
        return None

    depth_current = queue_info[pymqi.CMQC.MQIA_CURRENT_Q_DEPTH]
    depth_max = queue_info[pymqi.CMQC.MQIA_MAX_Q_DEPTH]

    depth_fraction = depth_current / depth_max

    return depth_fraction * 100


def _mq_datetime_to_seconds(channel_info, date_key, time_key):
    if (date_key not in channel_info) or (time_key not in channel_info):
        return None
    date_time_str = "{}_{}".format(
        ensure_unicode(channel_info[date_key]).strip(), ensure_unicode(channel_info[time_key]).strip()
    )
    dt = datetime.datetime.strptime(date_time_str, "%Y-%m-%d_%H.%M.%S")
    timestamp = (dt - datetime.datetime(1970, 1, 1)).total_seconds()
    return timestamp


def _alteration_datetime(channel_info):
    return _mq_datetime_to_seconds(channel_info, pymqi.CMQC.MQCA_ALTERATION_DATE, pymqi.CMQC.MQCA_ALTERATION_TIME)


def _last_message_datetime(channel_info):
    return _mq_datetime_to_seconds(channel_info, pymqi.CMQCFC.MQCACH_LAST_MSG_DATE, pymqi.CMQCFC.MQCACH_LAST_MSG_TIME)


QUEUE_MANAGER_METRICS = {
    'alteration_datetime': (_alteration_datetime, GAUGE),
    'dist_lists': (pymqi.CMQC.MQIA_DIST_LISTS, GAUGE),
    'max_msg_list': (pymqi.CMQC.MQIA_MAX_MSG_LENGTH, GAUGE),
}

QUEUE_MANAGER_STATUS_METRICS = {'connection_count': (pymqi.CMQCFC.MQIACF_CONNECTION_COUNT, GAUGE)}


QUEUE_METRICS = {
    'backout_threshold': (pymqi.CMQC.MQIA_BACKOUT_THRESHOLD, GAUGE),
    'depth_current': (pymqi.CMQC.MQIA_CURRENT_Q_DEPTH, GAUGE),
    'depth_high_event': (pymqi.CMQC.MQIA_Q_DEPTH_HIGH_EVENT, GAUGE),
    'depth_high_limit': (pymqi.CMQC.MQIA_Q_DEPTH_HIGH_LIMIT, GAUGE),
    'depth_low_event': (pymqi.CMQC.MQIA_Q_DEPTH_LOW_EVENT, GAUGE),
    'depth_low_limit': (pymqi.CMQC.MQIA_Q_DEPTH_LOW_LIMIT, GAUGE),
    'depth_max': (pymqi.CMQC.MQIA_MAX_Q_DEPTH, GAUGE),
    'depth_max_event': (pymqi.CMQC.MQIA_Q_DEPTH_MAX_EVENT, GAUGE),
    'depth_percent': (_depth_percent, GAUGE),
    'harden_get_backout': (pymqi.CMQC.MQIA_HARDEN_GET_BACKOUT, GAUGE),
    'inhibit_get': (pymqi.CMQC.MQIA_INHIBIT_GET, GAUGE),
    'inhibit_put': (pymqi.CMQC.MQIA_INHIBIT_PUT, GAUGE),
    'input_open_option': (pymqi.CMQC.MQIA_DEF_INPUT_OPEN_OPTION, GAUGE),
    'max_message_length': (pymqi.CMQC.MQIA_MAX_MSG_LENGTH, GAUGE),
    'message_delivery_sequence': (pymqi.CMQC.MQIA_MSG_DELIVERY_SEQUENCE, GAUGE),
    'open_input_count': (pymqi.CMQC.MQIA_OPEN_INPUT_COUNT, GAUGE),
    'open_output_count': (pymqi.CMQC.MQIA_OPEN_OUTPUT_COUNT, GAUGE),
    'persistence': (pymqi.CMQC.MQIA_DEF_PERSISTENCE, GAUGE),
    'priority': (pymqi.CMQC.MQIA_DEF_PRIORITY, GAUGE),
    'retention_interval': (pymqi.CMQC.MQIA_RETENTION_INTERVAL, GAUGE),
    'scope': (pymqi.CMQC.MQIA_SCOPE, GAUGE),
    'service_interval': (pymqi.CMQC.MQIA_Q_SERVICE_INTERVAL, GAUGE),
    'service_interval_event': (pymqi.CMQC.MQIA_Q_SERVICE_INTERVAL_EVENT, GAUGE),
    'trigger_control': (pymqi.CMQC.MQIA_TRIGGER_CONTROL, GAUGE),
    'trigger_depth': (pymqi.CMQC.MQIA_TRIGGER_DEPTH, GAUGE),
    'trigger_message_priority': (pymqi.CMQC.MQIA_TRIGGER_MSG_PRIORITY, GAUGE),
    'trigger_type': (pymqi.CMQC.MQIA_TRIGGER_TYPE, GAUGE),
    'type': (pymqi.CMQC.MQIA_Q_TYPE, GAUGE),
    'usage': (pymqi.CMQC.MQIA_USAGE, GAUGE),
}


QUEUE_STATUS_METRICS = {
    'oldest_message_age': (pymqi.CMQCFC.MQIACF_OLDEST_MSG_AGE, GAUGE),
    'uncommitted_msgs': (pymqi.CMQCFC.MQIACF_UNCOMMITTED_MSGS, GAUGE),
}

QUEUE_RESET_METRICS = {
    'high_q_depth': (pymqi.CMQC.MQIA_HIGH_Q_DEPTH, GAUGE),
    'msg_deq_count': (pymqi.CMQC.MQIA_MSG_DEQ_COUNT, RATE),
    'msg_enq_count': (pymqi.CMQC.MQIA_MSG_ENQ_COUNT, RATE),
    'time_since_reset': (pymqi.CMQC.MQIA_TIME_SINCE_RESET, RATE),
}

CHANNEL_METRICS = {
    'alteration_datetime': (_alteration_datetime, GAUGE),
    'batch_interval': (pymqi.CMQCFC.MQIACH_BATCH_INTERVAL, GAUGE),
    'batch_size': (pymqi.CMQCFC.MQIACH_BATCH_SIZE, GAUGE),
    'disc_interval': (pymqi.CMQCFC.MQIACH_DISC_INTERVAL, GAUGE),
    'hb_interval': (pymqi.CMQCFC.MQIACH_HB_INTERVAL, GAUGE),
    'keep_alive_interval': (pymqi.CMQCFC.MQIACH_KEEP_ALIVE_INTERVAL, GAUGE),
    'long_retry': (pymqi.CMQCFC.MQIACH_LONG_RETRY, GAUGE),
    'long_timer': (pymqi.CMQCFC.MQIACH_LONG_TIMER, GAUGE),
    'max_msg_length': (pymqi.CMQCFC.MQIACH_MAX_MSG_LENGTH, GAUGE),
    'mr_count': (pymqi.CMQCFC.MQIACH_MR_COUNT, GAUGE),
    'mr_interval': (pymqi.CMQCFC.MQIACH_MR_INTERVAL, GAUGE),
    'network_priority': (pymqi.CMQCFC.MQIACH_NETWORK_PRIORITY, GAUGE),
    'npm_speed': (pymqi.CMQCFC.MQIACH_NPM_SPEED, GAUGE),
    'sharing_conversations': (pymqi.CMQCFC.MQIACH_SHARING_CONVERSATIONS, GAUGE),
    'short_retry': (pymqi.CMQCFC.MQIACH_SHORT_RETRY, GAUGE),
    'short_timer': (pymqi.CMQCFC.MQIACH_SHORT_TIMER, GAUGE),
}

CHANNEL_STATUS_METRICS = {
    'buffers_rcvd': (pymqi.CMQCFC.MQIACH_BUFFERS_RCVD, GAUGE),
    'buffers_sent': (pymqi.CMQCFC.MQIACH_BUFFERS_SENT, GAUGE),
    'bytes_rcvd': (pymqi.CMQCFC.MQIACH_BYTES_RCVD, GAUGE),
    'bytes_sent': (pymqi.CMQCFC.MQIACH_BYTES_SENT, GAUGE),
    'channel_status': (pymqi.CMQCFC.MQIACH_CHANNEL_STATUS, GAUGE),
    'last_msg_datetime': (_last_message_datetime, GAUGE),
    'mca_status': (pymqi.CMQCFC.MQIACH_MCA_STATUS, GAUGE),
    'msgs': (pymqi.CMQCFC.MQIACH_MSGS, GAUGE),
    'ssl_key_resets': (pymqi.CMQCFC.MQIACH_SSL_KEY_RESETS, GAUGE),
    # TODO: Following metrics are NOT tested in e2e. I didn't managed to to get those metrics locally.
    'batches': (pymqi.CMQCFC.MQIACH_BATCHES, GAUGE),
    'current_msgs': (pymqi.CMQCFC.MQIACH_CURRENT_MSGS, GAUGE),
    'indoubt_status': (pymqi.CMQCFC.MQIACH_INDOUBT_STATUS, GAUGE),
}
