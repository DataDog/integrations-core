# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.checks.base import ServiceCheck
from datadog_checks.dev import get_docker_hostname

PROCESSES = ["program_0", "program_1", "program_2"]
STATUSES = ["down", "up", "unknown"]

HOST = get_docker_hostname()
PORT = 19001
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://{}:{}".format(HOST, PORT)

SUPERVISOR_VERSION = os.getenv('SUPERVISOR_VERSION')

# Supervisord should run 3 programs for 10, 20 and 30 seconds
# respectively.
# The following dictionnary shows the processes by state for each iteration.
PROCESSES_BY_STATE_BY_ITERATION = [dict(up=PROCESSES[x:], down=PROCESSES[:x], unknown=[]) for x in range(4)]

# Configs for Integration Tests
SUPERVISORD_CONFIG = {'name': "travis", 'host': HOST, 'port': '19001'}
BAD_SUPERVISORD_CONFIG = {'name': "travis", 'socket': "unix:///wrong/path/supervisor.sock", 'host': "http://127.0.0.1"}

# Configs for Unit/Mocked tests
TEST_CASES = [
    {
        'instances': [{'host': 'localhost', 'name': 'server1', 'port': 9001}],
        'expected_metrics': {
            'server1': [
                (
                    'supervisord.process.count',
                    1,
                    {'type': 'gauge', 'tags': ['supervisord_server:server1', 'status:up']},
                ),
                (
                    'supervisord.process.count',
                    1,
                    {'type': 'gauge', 'tags': ['supervisord_server:server1', 'status:down']},
                ),
                (
                    'supervisord.process.count',
                    1,
                    {'type': 'gauge', 'tags': ['supervisord_server:server1', 'status:unknown']},
                ),
                (
                    'supervisord.process.uptime',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server1', 'supervisord_process:python']},
                ),
                (
                    'supervisord.process.uptime',
                    125,
                    {'type': 'gauge', 'tags': ['supervisord_server:server1', 'supervisord_process:mysql']},
                ),
                (
                    'supervisord.process.uptime',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server1', 'supervisord_process:java']},
                ),
            ]
        },
        'expected_service_checks': {
            'server1': [
                {'status': ServiceCheck.OK, 'tags': ['supervisord_server:server1'], 'check': 'supervisord.can_connect'},
                {
                    'status': ServiceCheck.OK,
                    'tags': ['supervisord_server:server1', 'supervisord_process:mysql'],
                    'check': 'supervisord.process.status',
                },
                {
                    'status': ServiceCheck.CRITICAL,
                    'tags': ['supervisord_server:server1', 'supervisord_process:java'],
                    'check': 'supervisord.process.status',
                },
                {
                    'status': ServiceCheck.UNKNOWN,
                    'tags': ['supervisord_server:server1', 'supervisord_process:python'],
                    'check': 'supervisord.process.status',
                },
            ]
        },
    },
    {
        'instances': [
            {
                'name': 'server0',
                'host': 'localhost',
                'port': 9001,
                'user': 'user',
                'pass': 'pass',
                'proc_names': ['apache2', 'webapp'],
            },
            {'host': '10.60.130.82', 'name': 'server1'},
        ],
        'expected_metrics': {
            'server0': [
                (
                    'supervisord.process.count',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:up']},
                ),
                (
                    'supervisord.process.count',
                    2,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:down']},
                ),
                (
                    'supervisord.process.count',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:unknown']},
                ),
                (
                    'supervisord.process.uptime',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'supervisord_process:apache2']},
                ),
                (
                    'supervisord.process.uptime',
                    2,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'supervisord_process:webapp']},
                ),
            ],
            'server1': [
                (
                    'supervisord.process.count',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server1', 'status:up']},
                ),
                (
                    'supervisord.process.count',
                    1,
                    {'type': 'gauge', 'tags': ['supervisord_server:server1', 'status:down']},
                ),
                (
                    'supervisord.process.count',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server1', 'status:unknown']},
                ),
                (
                    'supervisord.process.uptime',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server1', 'supervisord_process:ruby']},
                ),
            ],
        },
        'expected_service_checks': {
            'server0': [
                {'status': ServiceCheck.OK, 'tags': ['supervisord_server:server0'], 'check': 'supervisord.can_connect'},
                {
                    'status': ServiceCheck.CRITICAL,
                    'tags': ['supervisord_server:server0', 'supervisord_process:apache2'],
                    'check': 'supervisord.process.status',
                },
                {
                    'status': ServiceCheck.CRITICAL,
                    'tags': ['supervisord_server:server0', 'supervisord_process:webapp'],
                    'check': 'supervisord.process.status',
                },
            ],
            'server1': [
                {'status': ServiceCheck.OK, 'tags': ['supervisord_server:server1'], 'check': 'supervisord.can_connect'},
                {
                    'status': ServiceCheck.CRITICAL,
                    'tags': ['supervisord_server:server1', 'supervisord_process:ruby'],
                    'check': 'supervisord.process.status',
                },
            ],
        },
    },
    {
        'instances': [{'name': 'server0', 'host': 'invalid_host', 'port': 9009}],
        'error_message': """Cannot connect to http://invalid_host:9009. Make sure supervisor is running and XML-RPC inet interface is enabled.""",  # noqa E501
    },
    {
        'instances': [
            {'name': 'server0', 'host': 'localhost', 'port': 9010, 'user': 'invalid_user', 'pass': 'invalid_pass'}
        ],
        'error_message': """Username or password to server0 are incorrect.""",
    },
    {
        'instances': [
            {'name': 'server0', 'host': 'localhost', 'port': 9001, 'proc_names': ['mysql', 'invalid_process']}
        ],
        'expected_metrics': {
            'server0': [
                (
                    'supervisord.process.count',
                    1,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:up']},
                ),
                (
                    'supervisord.process.count',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:down']},
                ),
                (
                    'supervisord.process.count',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:unknown']},
                ),
                (
                    'supervisord.process.uptime',
                    125,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'supervisord_process:mysql']},
                ),
            ]
        },
        'expected_service_checks': {
            'server0': [
                {'status': ServiceCheck.OK, 'tags': ['supervisord_server:server0'], 'check': 'supervisord.can_connect'},
                {
                    'status': ServiceCheck.OK,
                    'tags': ['supervisord_server:server0', 'supervisord_process:mysql'],
                    'check': 'supervisord.process.status',
                },
            ]
        },
    },
    {
        'instances': [
            {'name': 'server0', 'host': 'localhost', 'port': 9001, 'proc_regex': ['^mysq.$', 'invalid_process']}
        ],
        'expected_metrics': {
            'server0': [
                (
                    'supervisord.process.count',
                    1,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:up']},
                ),
                (
                    'supervisord.process.count',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:down']},
                ),
                (
                    'supervisord.process.count',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:unknown']},
                ),
                (
                    'supervisord.process.uptime',
                    125,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'supervisord_process:mysql']},
                ),
            ]
        },
        'expected_service_checks': {
            'server0': [
                {'status': ServiceCheck.OK, 'tags': ['supervisord_server:server0'], 'check': 'supervisord.can_connect'},
                {
                    'status': ServiceCheck.OK,
                    'tags': ['supervisord_server:server0', 'supervisord_process:mysql'],
                    'check': 'supervisord.process.status',
                },
            ]
        },
    },
    {
        'instances': [{'name': 'server0', 'host': 'localhost', 'port': 9001, 'proc_regex': '^mysq.$'}],
        'expected_metrics': {
            'server0': [
                (
                    'supervisord.process.count',
                    1,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:up']},
                ),
                (
                    'supervisord.process.count',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:down']},
                ),
                (
                    'supervisord.process.count',
                    0,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'status:unknown']},
                ),
                (
                    'supervisord.process.uptime',
                    125,
                    {'type': 'gauge', 'tags': ['supervisord_server:server0', 'supervisord_process:mysql']},
                ),
            ]
        },
        'expected_service_checks': {
            'server0': [
                {'status': ServiceCheck.OK, 'tags': ['supervisord_server:server0'], 'check': 'supervisord.can_connect'},
                {
                    'status': ServiceCheck.OK,
                    'tags': ['supervisord_server:server0', 'supervisord_process:mysql'],
                    'check': 'supervisord.process.status',
                },
            ]
        },
    },
]
