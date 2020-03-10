# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname
from datadog_checks.ibm_mq.metrics import COUNT, GAUGE

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_DIR = os.path.join(HERE, 'compose')

HOST = get_docker_hostname()
PORT = '11414'

USERNAME = 'admin'
PASSWORD = 'passw0rd'

QUEUE_MANAGER = 'datadog'
CHANNEL = 'DEV.ADMIN.SVRCONN'

QUEUE = 'DEV.QUEUE.1'

BAD_CHANNEL = 'DEV.NOTHERE.SVRCONN'

MQ_VERSION = os.environ.get('IBM_MQ_VERSION', '9')

COMPOSE_FILE_NAME = 'docker-compose-v{}.yml'.format(MQ_VERSION)

COMPOSE_FILE_PATH = os.path.join(COMPOSE_DIR, COMPOSE_FILE_NAME)

INSTANCE = {
    'channel': CHANNEL,
    'queue_manager': QUEUE_MANAGER,
    'host': HOST,
    'port': PORT,
    'username': USERNAME,
    'password': PASSWORD,
    'queues': [QUEUE],
    'channels': [CHANNEL, BAD_CHANNEL],
    'tags': ['foo:bar'],
}

INSTANCE_WITH_CONNECTION_NAME = {
    'channel': CHANNEL,
    'queue_manager': QUEUE_MANAGER,
    'connection_name': "{}({})".format(HOST, PORT),
    'username': USERNAME,
    'password': PASSWORD,
    'queues': [QUEUE],
    'channels': [CHANNEL, BAD_CHANNEL],
}

INSTANCE_QUEUE_PATTERN = {
    'channel': CHANNEL,
    'queue_manager': QUEUE_MANAGER,
    'host': HOST,
    'port': PORT,
    'username': USERNAME,
    'password': PASSWORD,
    'queue_patterns': ['DEV.*', 'SYSTEM.*'],
    'channels': [CHANNEL, BAD_CHANNEL],
}

INSTANCE_QUEUE_REGEX = {
    'channel': CHANNEL,
    'queue_manager': QUEUE_MANAGER,
    'host': HOST,
    'port': PORT,
    'username': USERNAME,
    'password': PASSWORD,
    'queue_regex': [r'^DEV\..*$', r'^SYSTEM\..*$'],
    'channels': [CHANNEL, BAD_CHANNEL],
}

INSTANCE_COLLECT_ALL = {
    'channel': CHANNEL,
    'queue_manager': QUEUE_MANAGER,
    'host': HOST,
    'port': PORT,
    'username': USERNAME,
    'password': PASSWORD,
    'auto_discover_queues': True,
    'channels': [CHANNEL, BAD_CHANNEL],
}

INSTANCE_QUEUE_REGEX_TAG = {
    'channel': CHANNEL,
    'queue_manager': QUEUE_MANAGER,
    'host': HOST,
    'port': PORT,
    'username': USERNAME,
    'password': PASSWORD,
    'queues': [QUEUE],
    'queue_tag_re': {'DEV.QUEUE.*': "foo:bar"},
}

E2E_METADATA = {
    # This script makes the necessary setup to be able to compile pymqi on the agent machine
    'start_commands': [
        'apt-get update',
        'apt-get install gcc -y',
        'mkdir /opt/mqm',
        'curl -L -o /opt/mqm/mq-client.tar.gz '
        'https://ddintegrations.blob.core.windows.net/ibm-mq/9.1.0.4-IBM-MQC-Redist-LinuxX64.tar.gz',
        'tar -C /opt/mqm -xf /opt/mqm/mq-client.tar.gz',
    ],
    'env_vars': {'LD_LIBRARY_PATH': '/opt/mqm/lib64:/opt/mqm/lib', 'C_INCLUDE_PATH': '/opt/mqm/inc'},
}

QUEUE_METRICS = [
    ('ibm_mq.queue.service_interval', GAUGE),
    ('ibm_mq.queue.inhibit_put', GAUGE),
    ('ibm_mq.queue.depth_low_limit', GAUGE),
    ('ibm_mq.queue.inhibit_get', GAUGE),
    ('ibm_mq.queue.harden_get_backout', GAUGE),
    ('ibm_mq.queue.service_interval_event', GAUGE),
    ('ibm_mq.queue.trigger_control', GAUGE),
    ('ibm_mq.queue.usage', GAUGE),
    ('ibm_mq.queue.scope', GAUGE),
    ('ibm_mq.queue.type', GAUGE),
    ('ibm_mq.queue.depth_max', GAUGE),
    ('ibm_mq.queue.backout_threshold', GAUGE),
    ('ibm_mq.queue.depth_high_event', GAUGE),
    ('ibm_mq.queue.depth_low_event', GAUGE),
    ('ibm_mq.queue.trigger_message_priority', GAUGE),
    ('ibm_mq.queue.depth_current', GAUGE),
    ('ibm_mq.queue.depth_max_event', GAUGE),
    ('ibm_mq.queue.open_input_count', GAUGE),
    ('ibm_mq.queue.persistence', GAUGE),
    ('ibm_mq.queue.trigger_depth', GAUGE),
    ('ibm_mq.queue.max_message_length', GAUGE),
    ('ibm_mq.queue.depth_high_limit', GAUGE),
    ('ibm_mq.queue.priority', GAUGE),
    ('ibm_mq.queue.input_open_option', GAUGE),
    ('ibm_mq.queue.message_delivery_sequence', GAUGE),
    ('ibm_mq.queue.retention_interval', GAUGE),
    ('ibm_mq.queue.open_output_count', GAUGE),
    ('ibm_mq.queue.trigger_type', GAUGE),
    ('ibm_mq.queue.depth_percent', GAUGE),
    ('ibm_mq.queue.high_q_depth', GAUGE),
    ('ibm_mq.queue.msg_deq_count', COUNT),
    ('ibm_mq.queue.msg_enq_count', COUNT),
    ('ibm_mq.queue.time_since_reset', COUNT),
]

QUEUE_STATUS_METRICS = [
    ('ibm_mq.queue.uncommitted_msgs', GAUGE),
]

CHANNEL_METRICS = [
    ('ibm_mq.channel.batch_size', GAUGE),
    ('ibm_mq.channel.batch_interval', GAUGE),
    ('ibm_mq.channel.long_retry', GAUGE),
    ('ibm_mq.channel.long_timer', GAUGE),
    ('ibm_mq.channel.max_message_length', GAUGE),
    ('ibm_mq.channel.short_retry', GAUGE),
    ('ibm_mq.channel.disc_interval', GAUGE),
    ('ibm_mq.channel.hb_interval', GAUGE),
    ('ibm_mq.channel.keep_alive_interval', GAUGE),
    ('ibm_mq.channel.mr_count', GAUGE),
    ('ibm_mq.channel.mr_interval', GAUGE),
    ('ibm_mq.channel.network_priority', GAUGE),
    ('ibm_mq.channel.npm_speed', GAUGE),
    ('ibm_mq.channel.sharing_conversations', GAUGE),
    ('ibm_mq.channel.short_timer', GAUGE),
]

CHANNEL_STATUS_METRICS = [
    ('ibm_mq.channel.buffers_rcvd', GAUGE),
    ('ibm_mq.channel.buffers_sent', GAUGE),
    ('ibm_mq.channel.bytes_rcvd', GAUGE),
    ('ibm_mq.channel.bytes_sent', GAUGE),
    ('ibm_mq.channel.channel_status', GAUGE),
    ('ibm_mq.channel.mca_status', GAUGE),
    ('ibm_mq.channel.msgs', GAUGE),
    ('ibm_mq.channel.ssl_key_resets', GAUGE),
]

METRICS = (
    [
        ('ibm_mq.queue_manager.dist_lists', GAUGE),
        ('ibm_mq.queue_manager.max_msg_list', GAUGE),
        ('ibm_mq.channel.channels', GAUGE),
        ('ibm_mq.channel.count', GAUGE),
    ]
    + QUEUE_METRICS
    + QUEUE_STATUS_METRICS
    + CHANNEL_METRICS
    + CHANNEL_STATUS_METRICS
)

OPTIONAL_METRICS = [
    'ibm_mq.queue.max_channels',
]


def assert_all_metrics(aggregator):
    for metric, metric_type in METRICS:
        aggregator.assert_metric(metric, metric_type=getattr(aggregator, metric_type.upper()))

    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
