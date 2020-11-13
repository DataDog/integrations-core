# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import division

try:
    import pymqi
except ImportError:
    pymqi = None

# Metric types
GAUGE = 'gauge'
COUNT = 'count'

METRIC_PREFIX = 'ibm_mq'


def queue_metrics():
    return {
        # 'service_interval': pymqi.CMQC.MQIA_Q_SERVICE_INTERVAL,
        # 'inhibit_put': pymqi.CMQC.MQIA_INHIBIT_PUT,
        # 'depth_low_limit': pymqi.CMQC.MQIA_Q_DEPTH_LOW_LIMIT,
        # 'inhibit_get': pymqi.CMQC.MQIA_INHIBIT_GET,
        # 'harden_get_backout': pymqi.CMQC.MQIA_HARDEN_GET_BACKOUT,
        # 'service_interval_event': pymqi.CMQC.MQIA_Q_SERVICE_INTERVAL_EVENT,
        # 'trigger_control': pymqi.CMQC.MQIA_TRIGGER_CONTROL,
        # 'usage': pymqi.CMQC.MQIA_USAGE,
        # 'scope': pymqi.CMQC.MQIA_SCOPE,
        # 'type': pymqi.CMQC.MQIA_Q_TYPE,
        # 'depth_max': pymqi.CMQC.MQIA_MAX_Q_DEPTH,
        # 'backout_threshold': pymqi.CMQC.MQIA_BACKOUT_THRESHOLD,
        # 'depth_high_event': pymqi.CMQC.MQIA_Q_DEPTH_HIGH_EVENT,
        # 'depth_low_event': pymqi.CMQC.MQIA_Q_DEPTH_LOW_EVENT,
        # 'trigger_message_priority': pymqi.CMQC.MQIA_TRIGGER_MSG_PRIORITY,
        # 'depth_current': pymqi.CMQC.MQIA_CURRENT_Q_DEPTH,
        # 'depth_max_event': pymqi.CMQC.MQIA_Q_DEPTH_MAX_EVENT,
        # 'open_input_count': pymqi.CMQC.MQIA_OPEN_INPUT_COUNT,
        # 'persistence': pymqi.CMQC.MQIA_DEF_PERSISTENCE,
        # 'trigger_depth': pymqi.CMQC.MQIA_TRIGGER_DEPTH,
        # 'max_message_length': pymqi.CMQC.MQIA_MAX_MSG_LENGTH,
        # 'depth_high_limit': pymqi.CMQC.MQIA_Q_DEPTH_HIGH_LIMIT,
        # 'priority': pymqi.CMQC.MQIA_DEF_PRIORITY,
        # 'input_open_option': pymqi.CMQC.MQIA_DEF_INPUT_OPEN_OPTION,
        # 'message_delivery_sequence': pymqi.CMQC.MQIA_MSG_DELIVERY_SEQUENCE,
        # 'retention_interval': pymqi.CMQC.MQIA_RETENTION_INTERVAL,
        # 'open_output_count': pymqi.CMQC.MQIA_OPEN_OUTPUT_COUNT,
        # 'trigger_type': pymqi.CMQC.MQIA_TRIGGER_TYPE,
        # 'depth_percent': depth_percent,
    }


def pcf_metrics():
    return {
        # 'oldest_message_age': {'pymqi_value': pymqi.CMQCFC.MQIACF_OLDEST_MSG_AGE, 'failure': -1},
        # 'uncommitted_msgs': {'pymqi_value': pymqi.CMQCFC.MQIACF_UNCOMMITTED_MSGS, 'failure': -1},
    }


def pcf_status_reset_metrics():
    return {
        # 'high_q_depth': (pymqi.CMQC.MQIA_HIGH_Q_DEPTH, GAUGE),
        # 'msg_deq_count': (pymqi.CMQC.MQIA_MSG_DEQ_COUNT, COUNT),
        # 'msg_enq_count': (pymqi.CMQC.MQIA_MSG_ENQ_COUNT, COUNT),
        # 'time_since_reset': (pymqi.CMQC.MQIA_TIME_SINCE_RESET, COUNT),
    }


def queue_manager_metrics():
    return {
        # 'dist_lists': pymqi.CMQC.MQIA_DIST_LISTS, 'max_msg_list': pymqi.CMQC.MQIA_MAX_MSG_LENGTH
    }


def channel_metrics():
    return {
        'batch_size': pymqi.CMQCFC.MQIACH_BATCH_SIZE,
        'batch_interval': pymqi.CMQCFC.MQIACH_BATCH_INTERVAL,
        'long_retry': pymqi.CMQCFC.MQIACH_LONG_RETRY,
        'long_timer': pymqi.CMQCFC.MQIACH_LONG_TIMER,
        'max_message_length': pymqi.CMQCFC.MQIACH_MAX_MSG_LENGTH,
        'short_retry': pymqi.CMQCFC.MQIACH_SHORT_RETRY,
        'disc_interval': pymqi.CMQCFC.MQIACH_DISC_INTERVAL,
        'hb_interval': pymqi.CMQCFC.MQIACH_HB_INTERVAL,
        'keep_alive_interval': pymqi.CMQCFC.MQIACH_KEEP_ALIVE_INTERVAL,
        'mr_count': pymqi.CMQCFC.MQIACH_MR_COUNT,
        'mr_interval': pymqi.CMQCFC.MQIACH_MR_INTERVAL,
        'network_priority': pymqi.CMQCFC.MQIACH_NETWORK_PRIORITY,
        'npm_speed': pymqi.CMQCFC.MQIACH_NPM_SPEED,
        'sharing_conversations': pymqi.CMQCFC.MQIACH_SHARING_CONVERSATIONS,
        'short_timer': pymqi.CMQCFC.MQIACH_SHORT_TIMER,
    }


def channel_status_metrics():
    return {
        'buffers_rcvd': pymqi.CMQCFC.MQIACH_BUFFERS_RCVD,
        'buffers_sent': pymqi.CMQCFC.MQIACH_BUFFERS_SENT,
        'bytes_rcvd': pymqi.CMQCFC.MQIACH_BYTES_RCVD,
        'bytes_sent': pymqi.CMQCFC.MQIACH_BYTES_SENT,
        'channel_status': pymqi.CMQCFC.MQIACH_CHANNEL_STATUS,
        'mca_status': pymqi.CMQCFC.MQIACH_MCA_STATUS,
        'msgs': pymqi.CMQCFC.MQIACH_MSGS,
        'ssl_key_resets': pymqi.CMQCFC.MQIACH_SSL_KEY_RESETS,
        'batches': pymqi.CMQCFC.MQIACH_BATCHES,
        'current_msgs': pymqi.CMQCFC.MQIACH_CURRENT_MSGS,
        'indoubt_status': pymqi.CMQCFC.MQIACH_INDOUBT_STATUS,
    }


def channel_stats_metrics():
    return {
        # Most stats metrics are count since we want to add up the values
        # if there are multiple messages of same type for a single check run.
        'msgs': (pymqi.CMQCFC.MQIAMO_MSGS, COUNT),
        'bytes': (pymqi.CMQCFC.MQIAMO64_BYTES, COUNT),
        'put_retries': (pymqi.CMQCFC.MQIAMO_PUT_RETRIES, COUNT),
        # Following metrics are currently not covered by e2e tests
        'full_batches': (pymqi.CMQCFC.MQIAMO_FULL_BATCHES, COUNT),
        'incomplete_batches': (pymqi.CMQCFC.MQIAMO_INCOMPLETE_BATCHES, COUNT),
        'avg_batch_size': (pymqi.CMQCFC.MQIAMO_AVG_BATCH_SIZE, GAUGE),
    }


def queue_stats_metrics():
    return {
        # 'q_min_depth': (pymqi.CMQCFC.MQIAMO_Q_MIN_DEPTH, GAUGE),
        # 'q_max_depth': (pymqi.CMQCFC.MQIAMO_Q_MAX_DEPTH, GAUGE),
        # 'q_type': (pymqi.CMQC.MQIA_Q_TYPE, GAUGE),
        'avg_q_time': (pymqi.CMQCFC.MQIAMO64_AVG_Q_TIME, GAUGE),  # this is a list
        'put_count': (pymqi.CMQCFC.MQIAMO_PUTS, COUNT)  # this is a list
    }


def depth_percent(queue_info):
    if pymqi.CMQC.MQIA_CURRENT_Q_DEPTH not in queue_info or pymqi.CMQC.MQIA_MAX_Q_DEPTH not in queue_info:
        return None

    depth_current = queue_info[pymqi.CMQC.MQIA_CURRENT_Q_DEPTH]
    depth_max = queue_info[pymqi.CMQC.MQIA_MAX_Q_DEPTH]

    depth_fraction = depth_current / depth_max
    depth_as_percent = depth_fraction * 100

    return depth_as_percent
