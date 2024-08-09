# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.tibco_ems.constants import SHOW_METRIC_DATA

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE = os.path.join(HERE, 'compose')
ROOT = os.path.dirname(os.path.dirname(HERE))


CHECK_NAME = 'tibco_ems'

HOST = get_docker_hostname()
PORT = 7222

METRIC_DATA = [
    'tibco_ems.connection.consumers',
    'tibco_ems.connection.producers',
    'tibco_ems.connection.sessions',
    'tibco_ems.connection.temporary_queues',
    'tibco_ems.connection.temporary_topics',
    'tibco_ems.connection.uncommitted_transactions',
    'tibco_ems.connection.uncommitted_transactions_size',
    'tibco_ems.consumer.messages_rate',
    'tibco_ems.consumer.messages_rate_size',
    'tibco_ems.consumer.total_messages',
    'tibco_ems.consumer.total_messages_size',
    'tibco_ems.durable.pending_messages',
    'tibco_ems.durable.pending_messages_size',
    'tibco_ems.producer.messages_rate',
    'tibco_ems.producer.messages_rate_size',
    'tibco_ems.producer.total_messages',
    'tibco_ems.producer.total_messages_size',
    'tibco_ems.queue.pending_messages',
    'tibco_ems.queue.pending_messages_size',
    'tibco_ems.queue.pending_persistent_messages',
    'tibco_ems.queue.pending_persistent_messages_size',
    'tibco_ems.queue.receivers',
    'tibco_ems.server.admin_connections',
    'tibco_ems.server.asynchronous_storage',
    'tibco_ems.server.client_connections',
    'tibco_ems.server.consumers',
    'tibco_ems.server.durables',
    'tibco_ems.server.inbound_message_rate',
    'tibco_ems.server.inbound_message_rate_size',
    'tibco_ems.server.message_memory_pooled',
    'tibco_ems.server.outbound_message_rate',
    'tibco_ems.server.outbound_message_rate_size',
    'tibco_ems.server.pending_messages',
    'tibco_ems.server.pending_message_size',
    'tibco_ems.server.producers',
    'tibco_ems.server.queues',
    'tibco_ems.server.sessions',
    'tibco_ems.server.synchronous_storage',
    'tibco_ems.server.topics',
    'tibco_ems.server.uptime',
    'tibco_ems.server.storage_read_rate',
    'tibco_ems.server.storage_read_rate_size',
    'tibco_ems.server.storage_write_rate',
    'tibco_ems.server.storage_write_rate_size',
    'tibco_ems.topic.durable_subscriptions',
    'tibco_ems.topic.pending_messages',
    'tibco_ems.topic.pending_messages_size',
    'tibco_ems.topic.pending_persistent_messages',
    'tibco_ems.topic.pending_persistent_messages_size',
    'tibco_ems.topic.subsciptions',
]


def _read_fixture(filename):
    with open(os.path.join(HERE, 'fixtures', filename)) as f:
        contents = f.read()
        return contents.encode('utf-8')


def mock_output(filename):
    return _read_fixture(filename)


SHOW_MAP = {
    'show server': {
        'section': mock_output('show_server'),
        'regex': SHOW_METRIC_DATA['show server']['regex'],
        'expected_result': {
            'version': '10.1.0',
            'server': 'tibemsd (version: 10.1.0 V4)',
            'hostname': 'd3ce69f9df4f',
            'process_id': 1,
            'state': 'active',
            'runtime_module_path': '/opt/tibco/ems/10.1/bin/lib:/opt/tibco/ems/10.1/lib',
            'topics': 3,
            'queues': 9,
            'client_connections': 0,
            'admin_connections': 2,
            'sessions': 2,
            'producers': 2,
            'consumers': 2,
            'durables': 1,
            'log_file_size': '19.4 Kb out of 1MB',
            'pending_messages': 0,
            'pending_message_size': {'value': 0.0, 'unit': 'Kb'},
            'message_memory_usage': {'value': 25.4, 'unit': 'Kb'},
            'message_memory_pooled': {'value': 53.0, 'unit': 'Kb'},
            'synchronous_storage': {'value': 1.5, 'unit': 'Kb'},
            'asynchronous_storage': {'value': 3.5, 'unit': 'Kb'},
            'fsync_for_sync_storage': 'disabled',
            'inbound_message_rate': 0.0,
            'inbound_message_rate_size': {'value': 0.0, 'unit': 'Kb'},
            'outbound_message_rate': 0.0,
            'outbound_message_rate_size': {'value': 0.0, 'unit': 'Kb'},
            'storage_read_rate': 0.0,
            'storage_read_rate_size': {'value': 0.0, 'unit': 'Kb'},
            'storage_write_rate': 0.0,
            'storage_write_rate_size': {'value': 0.0, 'unit': 'Kb'},
            'uptime': 368340,
        },
        'expected_metrics': [
            'tibco_ems.server.admin_connections',
            'tibco_ems.server.asynchronous_storage',
            'tibco_ems.server.client_connections',
            'tibco_ems.server.consumers',
            'tibco_ems.server.durables',
            'tibco_ems.server.inbound_message_rate',
            'tibco_ems.server.inbound_message_rate_size',
            'tibco_ems.server.message_memory_pooled',
            'tibco_ems.server.outbound_message_rate',
            'tibco_ems.server.outbound_message_rate_size',
            'tibco_ems.server.pending_messages',
            'tibco_ems.server.pending_message_size',
            'tibco_ems.server.producers',
            'tibco_ems.server.queues',
            'tibco_ems.server.sessions',
            'tibco_ems.server.synchronous_storage',
            'tibco_ems.server.topics',
            'tibco_ems.server.uptime',
            'tibco_ems.server.storage_read_rate',
            'tibco_ems.server.storage_read_rate_size',
            'tibco_ems.server.storage_write_rate',
            'tibco_ems.server.storage_write_rate_size',
        ],
    },
    'show queues': {
        'section': mock_output('show_queues'),
        'regex': SHOW_METRIC_DATA['show queues']['regex'],
        'expected_result': [
            {
                'pending_messages': 0,
                'pending_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pending_persistent_messages': 0,
                'pending_persistent_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pre': 5,
                'queue_name': 'hash_queue',
                'receivers': 0,
                'snfgxibct': '',
            },
            {
                'pending_messages': 0,
                'pending_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pending_persistent_messages': 0,
                'pending_persistent_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pre': 5,
                'queue_name': 'sys.admin',
                'receivers': 0,
                'snfgxibct': '',
            },
            {
                'pending_messages': 0,
                'pending_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pending_persistent_messages': 0,
                'pending_persistent_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pre': 5,
                'queue_name': 'sys.lookup',
                'receivers': 0,
                'snfgxibct': '',
            },
            {
                'pending_messages': 0,
                'pending_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pending_persistent_messages': 0,
                'pending_persistent_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pre': 5,
                'queue_name': 'sys.redelivery.delay',
                'receivers': 0,
                'snfgxibct': '',
            },
            {
                'pending_messages': 0,
                'pending_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pending_persistent_messages': 0,
                'pending_persistent_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pre': 5,
                'queue_name': 'sys.undelivered',
                'receivers': 0,
                'snfgxibct': '',
            },
            {
                'queue_name': 'TMP.tibemsd.1669EC51B3.1',
                'receivers': 1,
                'snfgxibct': '',
                'pending_messages': 0,
                'pending_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pending_persistent_messages': 0,
                'pending_persistent_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pre': 5,
            },
            {
                'pending_messages': 0,
                'pending_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pending_persistent_messages': 0,
                'pending_persistent_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pre': 5,
                'queue_name': 'queue.sample',
                'receivers': 0,
                'snfgxibct': '',
            },
            {
                'pending_messages': 0,
                'pending_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pending_persistent_messages': 0,
                'pending_persistent_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pre': 5,
                'queue_name': 'sample',
                'receivers': 0,
                'snfgxibct': '',
            },
        ],
        'expected_metrics': [
            'tibco_ems.queue.pending_messages',
            'tibco_ems.queue.pending_messages_size',
            'tibco_ems.queue.pending_persistent_messages',
            'tibco_ems.queue.pending_persistent_messages_size',
            'tibco_ems.queue.receivers',
        ],
    },
    'show topics': {
        'section': mock_output('show_topics'),
        'regex': SHOW_METRIC_DATA['show topics']['regex'],
        'expected_result': [
            {
                'durable_subscriptions': 1,
                'pending_messages': 0,
                'pending_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pending_persistent_messages': 0,
                'pending_persistent_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'snfgeibctm': '',
                'subsciptions': 1,
                'topic_name': 'sample',
            },
            {
                'durable_subscriptions': 0,
                'pending_messages': 0,
                'pending_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'pending_persistent_messages': 0,
                'pending_persistent_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'snfgeibctm': '',
                'subsciptions': 0,
                'topic_name': 'topic.sample',
            },
        ],
        'expected_metrics': [
            'tibco_ems.topic.durable_subscriptions',
            'tibco_ems.topic.pending_messages',
            'tibco_ems.topic.pending_messages_size',
            'tibco_ems.topic.pending_persistent_messages',
            'tibco_ems.topic.pending_persistent_messages_size',
            'tibco_ems.topic.subsciptions',
        ],
    },
    'show stat consumers': {
        'section': mock_output('show_stat_consumers'),
        'regex': SHOW_METRIC_DATA['show stat consumers']['regex'],
        'expected_result': [
            {
                'user': 'admin',
                'component_type': 'Q',
                'conn': 2,
                'destination': 'TMP.tibemsd.1669EC51B3.1',
                'total_messages': 1,
                'total_messages_size': {'value': 2.4, 'unit': 'Kb'},
                'messages_rate': 0,
                'messages_rate_size': {'value': 0.6, 'unit': 'Kb'},
            }
        ],
        'expected_metrics': [
            'tibco_ems.consumer.messages_rate',
            'tibco_ems.consumer.messages_rate_size',
            'tibco_ems.consumer.total_messages',
            'tibco_ems.consumer.total_messages_size',
        ],
    },
    'show stat producers': {
        'section': mock_output('show_stat_producers'),
        'regex': SHOW_METRIC_DATA['show stat producers']['regex'],
        'expected_result': [
            {
                'user': 'admin',
                'conn': 2,
                'component_type': 'Q',
                'destination': 'sys.admin',
                'total_messages': 3,
                'total_messages_size': {'value': 0.5, 'unit': 'Kb'},
                'messages_rate': 0,
                'messages_rate_size': {'value': 0.0, 'unit': 'Kb'},
            }
        ],
        'expected_metrics': [
            'tibco_ems.producer.messages_rate',
            'tibco_ems.producer.messages_rate_size',
            'tibco_ems.producer.total_messages',
            'tibco_ems.producer.total_messages_size',
        ],
    },
    'show connections full': {
        'section': mock_output('show_connections'),
        'regex': SHOW_METRIC_DATA['show connections full']['regex'],
        'expected_result': [
            {
                'client_id': '',
                'client_type': 'C',
                'consumers': 1,
                'fsxt': 'A',
                'id': 2,
                'ip_address': '127.0.0.1',
                'tibco_port': 33696,
                'producers': 1,
                's': '',
                'sessions': 1,
                'temporary_queues': 1,
                'temporary_topics': 0,
                'tibco_host': 'd3ce69f9df4f',
                'tibco_version': '10.1.0V4',
                'uncommitted_transactions': 0,
                'uncommitted_transactions_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'uptime': 247,
                'user': 'admin',
            },
        ],
        'expected_metrics': [
            'tibco_ems.connection.consumers',
            'tibco_ems.connection.producers',
            'tibco_ems.connection.sessions',
            'tibco_ems.connection.temporary_queues',
            'tibco_ems.connection.temporary_topics',
            'tibco_ems.connection.uncommitted_transactions',
            'tibco_ems.connection.uncommitted_transactions_size',
        ],
    },
    'show durables': {
        'section': mock_output('show_durables'),
        'regex': SHOW_METRIC_DATA['show durables']['regex'],
        'expected_result': [
            {
                'durable': 'sample.durable',
                'pending_messages': 0,
                'pending_messages_size': {
                    'unit': 'Kb',
                    'value': 0.0,
                },
                'shared': 'N',
                'topic_name': 'sample',
                'user': 'offline',
            },
        ],
        'expected_metrics': [
            'tibco_ems.durable.pending_messages',
            'tibco_ems.durable.pending_messages_size',
        ],
    },
}
