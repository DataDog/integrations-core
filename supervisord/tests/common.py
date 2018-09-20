# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.checks.base import AgentCheck
from datadog_checks.supervisord.supervisord import SupervisordCheck


CHECK_NAME = 'supervisord'
PROCESSES = ["program_0", "program_1", "program_2"]
STATUSES = ["down", "up", "unknown"]

supervisor_check = SupervisordCheck(CHECK_NAME, {}, {})

# Configs for Integration Tests
SUPERVISORD_CONFIG = {'name': "travis", 'host': "localhost", 'port': '19001'}
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
                {'status': AgentCheck.OK, 'tags': ['supervisord_server:server1'], 'check': 'supervisord.can_connect'},
                {
                    'status': AgentCheck.OK,
                    'tags': ['supervisord_server:server1', 'supervisord_process:mysql'],
                    'check': 'supervisord.process.status',
                },
                {
                    'status': AgentCheck.CRITICAL,
                    'tags': ['supervisord_server:server1', 'supervisord_process:java'],
                    'check': 'supervisord.process.status',
                },
                {
                    'status': AgentCheck.UNKNOWN,
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
                {'status': AgentCheck.OK, 'tags': ['supervisord_server:server0'], 'check': 'supervisord.can_connect'},
                {
                    'status': AgentCheck.CRITICAL,
                    'tags': ['supervisord_server:server0', 'supervisord_process:apache2'],
                    'check': 'supervisord.process.status',
                },
                {
                    'status': AgentCheck.CRITICAL,
                    'tags': ['supervisord_server:server0', 'supervisord_process:webapp'],
                    'check': 'supervisord.process.status',
                },
            ],
            'server1': [
                {'status': AgentCheck.OK, 'tags': ['supervisord_server:server1'], 'check': 'supervisord.can_connect'},
                {
                    'status': AgentCheck.CRITICAL,
                    'tags': ['supervisord_server:server1', 'supervisord_process:ruby'],
                    'check': 'supervisord.process.status',
                },
            ],
        },
    },
    {
        'instances': [{'name': 'server0', 'host': 'invalid_host', 'port': 9009}],
        'error_message': """Cannot connect to http://invalid_host:9009. Make sure supervisor is running and XML-RPC inet interface is enabled.""", # noqa E501
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
                {'status': AgentCheck.OK, 'tags': ['supervisord_server:server0'], 'check': 'supervisord.can_connect'},
                {
                    'status': AgentCheck.OK,
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
                {'status': AgentCheck.OK, 'tags': ['supervisord_server:server0'], 'check': 'supervisord.can_connect'},
                {
                    'status': AgentCheck.OK,
                    'tags': ['supervisord_server:server0', 'supervisord_process:mysql'],
                    'check': 'supervisord.process.status',
                },
            ]
        },
    },
]
