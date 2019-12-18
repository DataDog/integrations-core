# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname

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
    'start_commands': [
        'mkdir /opt/mqm',
        'curl -o /opt/mqm/mq-client.tar.gz '
        'https://dd-agent-tarball-mirror.s3.amazonaws.com/9.0.0.6-IBM-MQC-Redist-LinuxX64.tar.gz',
        'tar -C /opt/mqm -xf /opt/mqm/mq-client.tar.gz',
    ],
    'env_vars': {'LD_LIBRARY_PATH': '/opt/mqm/lib64:/opt/mqm/lib'},
}


QUEUE_METRICS = [
    'ibm_mq.queue.service_interval',
    'ibm_mq.queue.inhibit_put',
    'ibm_mq.queue.depth_low_limit',
    'ibm_mq.queue.inhibit_get',
    'ibm_mq.queue.harden_get_backout',
    'ibm_mq.queue.service_interval_event',
    'ibm_mq.queue.trigger_control',
    'ibm_mq.queue.usage',
    'ibm_mq.queue.scope',
    'ibm_mq.queue.type',
    'ibm_mq.queue.depth_max',
    'ibm_mq.queue.backout_threshold',
    'ibm_mq.queue.depth_high_event',
    'ibm_mq.queue.depth_low_event',
    'ibm_mq.queue.trigger_message_priority',
    'ibm_mq.queue.depth_current',
    'ibm_mq.queue.depth_max_event',
    'ibm_mq.queue.open_input_count',
    'ibm_mq.queue.persistence',
    'ibm_mq.queue.trigger_depth',
    'ibm_mq.queue.max_message_length',
    'ibm_mq.queue.depth_high_limit',
    'ibm_mq.queue.priority',
    'ibm_mq.queue.input_open_option',
    'ibm_mq.queue.message_delivery_sequence',
    'ibm_mq.queue.retention_interval',
    'ibm_mq.queue.open_output_count',
    'ibm_mq.queue.trigger_type',
    'ibm_mq.queue.depth_percent',
    'ibm_mq.queue.high_q_depth',
    'ibm_mq.queue.msg_deq_count',
    'ibm_mq.queue.msg_enq_count',
    'ibm_mq.queue.time_since_reset',
]

QUEUE_STATUS_METRICS = ['ibm_mq.queue.uncommitted_msgs']

CHANNEL_METRICS = [
    'ibm_mq.channel.batch_size',
    'ibm_mq.channel.batch_interval',
    'ibm_mq.channel.long_retry',
    'ibm_mq.channel.long_timer',
    'ibm_mq.channel.max_message_length',
    'ibm_mq.channel.short_retry',
    'ibm_mq.channel.disc_interval',
    'ibm_mq.channel.hb_interval',
    'ibm_mq.channel.keep_alive_interval',
    'ibm_mq.channel.mr_count',
    'ibm_mq.channel.mr_interval',
    'ibm_mq.channel.network_priority',
    'ibm_mq.channel.npm_speed',
    'ibm_mq.channel.sharing_conversations',
    'ibm_mq.channel.short_timer',
]

CHANNEL_STATUS_METRICS = [
    'ibm_mq.channel.buffers_rcvd',
    'ibm_mq.channel.buffers_sent',
    'ibm_mq.channel.bytes_rcvd',
    'ibm_mq.channel.bytes_sent',
    'ibm_mq.channel.channel_status',
    'ibm_mq.channel.mca_status',
    'ibm_mq.channel.msgs',
    'ibm_mq.channel.ssl_key_resets',
]

METRICS = (
    [
        'ibm_mq.queue_manager.dist_lists',
        'ibm_mq.queue_manager.max_msg_list',
        'ibm_mq.channel.channels',
        'ibm_mq.channel.count',
    ]
    + QUEUE_METRICS
    + QUEUE_STATUS_METRICS
    + CHANNEL_METRICS
    + CHANNEL_STATUS_METRICS
)

OPTIONAL_METRICS = [
    'ibm_mq.queue.max_channels',
]
