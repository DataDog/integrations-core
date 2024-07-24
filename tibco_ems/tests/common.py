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
        return contents, "", 0


def mock_output(filename):
    return _read_fixture(filename)


SHOW_MAP = {
    'show server': {
        'output': mock_output('show_server')[0],
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
    },
    'show queues': {
        'output': mock_output('show_queues')[0],
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
    },
    'show topics': {
        'output': mock_output('show_topics')[0],
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
    },
    'show stat consumers': {
        'output': mock_output('show_stat_consumers')[0],
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
    },
    'show stat producers': {
        'output': mock_output('show_stat_producers')[0],
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
    },
    'show connections full': {
        'output': mock_output('show_connections')[0],
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
    },
}

SECTION_RESULT = {
    'show server': ' Server:                   tibemsd (version: 10.1.0 V4)\n Hostname:                 d3ce69f9df4f\n Process Id:               1\n State:                    active\n Runtime Module Path:      /opt/tibco/ems/10.1/bin/lib:/opt/tibco/ems/10.1/lib\n Topics:                   3 (0 dynamic, 0 temporary)\n Queues:                   10 (0 dynamic, 1 temporary)\n Client Connections:       0\n Admin Connections:        1\n Sessions:                 1\n Producers:                1\n Consumers:                1\n Durables:                 1\n Log File Size:            85.8 Kb out of 1MB\n Pending Messages:         0\n Pending Message Size:     0.0 Kb\n Message Memory Usage:     16.6 Kb out of 512MB\n Message Memory Pooled:    53.0 Kb\n Synchronous Storage:      1.5 Kb\n Asynchronous Storage:     3.5 Kb\n Fsync for Sync Storage:   disabled\n Inbound Message Rate:     0 msgs/sec,  0.0 Kb per second\n Outbound Message Rate:    0 msgs/sec,  0.0 Kb per second\n Storage Read Rate:        0 reads/sec,  0.0 Kb per second\n Storage Write Rate:       0 writes/sec, 0.0 Kb per second\n Uptime:                   18 days 11 hours 23 minutes',  # noqa
    'show queues': '                                                              All Msgs            Persistent Msgs\n  Queue Name                        SNFGXIBCT  Pre  Rcvrs     Msgs    Size        Msgs    Size\n  >                                 ---------    5*     0        0     0.0 Kb        0     0.0 Kb\n  !hash_queue#                      ---------    5*     0        0     0.0 Kb        0     0.0 Kb\n  #hash_queue#                      ---------    5*     0        0     0.0 Kb        0     0.0 Kb\n  $sys.admin                        +--------    5*     0        0     0.0 Kb        0     0.0 Kb\n  $sys.lookup                       ---------    5*     0        0     0.0 Kb        0     0.0 Kb\n  $sys.redelivery.delay             +--------    5*     0        0     0.0 Kb        0     0.0 Kb\n  $sys.undelivered                  +--------    5*     0        0     0.0 Kb        0     0.0 Kb\n* $TMP$.tibemsd.16675855A2984.1     ---------    5      1        0     0.0 Kb        0     0.0 Kb\n  queue.sample                      -------+-    5*     0        0     0.0 Kb        0     0.0 Kb\n  sample                            -------+-    5*     0        0     0.0 Kb        0     0.0 Kb',  # noqa
    'show topics': '                                                               All Msgs            Persistent Msgs\n  Topic Name                        SNFGEIBCTM  Subs  Durs     Msgs    Size        Msgs    Size\n  >                                 ----------     0     0        0     0.0 Kb        0     0.0 Kb\n  sample                            -------+--     1     1        0     0.0 Kb        0     0.0 Kb\n  topic.sample                      -------+--     0     0        0     0.0 Kb        0     0.0 Kb',  # noqa
    'show stat consumers': '                                                      Total Count      Rate/Second\n  User       Conn  T  Destination                      Msgs   Size      Msgs   Size\n  admin         2  Q  $TMP$.tibemsd.1669EC51B3.1          1    2.4 Kb      0    0.6 Kb',  # noqa
    'show stat producers': '                                        Total Count      Rate/Second\n  User       Conn  T  Destination       Msgs   Size      Msgs   Size\n  admin         2  Q  $sys.admin           3    0.5 Kb      0    0.0 Kb',  # noqa
    'show connections full': 'L  Version   ID    FSXT  S  Host         IP address Port  User   ClientID Sess Prod Cons TmpT TmpQ Uncomm UncommSize     Uptime\nC  10.1.0 V4 10630 ---A  +  d3ce69f9df4f 127.0.0.1  46418 admin              1    1    1    0    1      0     0.0 Kb      0.030',  # noqa
    'show durables': '  Topic Name        Durable          Shared  User         Msgs    Size\n  sample            sample.durable   N       <offline>       0     0.0 Kb',  # noqa
}

SECTION_OUTPUT_SHOW_ALL = mock_output('show_all')[0]
