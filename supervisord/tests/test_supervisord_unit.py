# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.supervisord.supervisord import FORMAT_TIME  # pylint: disable=import-error,no-name-in-module
from mock import patch
import pytest
from socket import socket
import xmlrpclib
from .common import (
    TEST_CASES,
    supervisor_check
)


# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit


def mock_server(url):
    return MockXmlRcpServer(url)


@patch('xmlrpclib.Server', side_effect=mock_server)
def test_check(mock_server, aggregator):
    """Integration test for supervisord check. Using a mocked supervisord."""

    for tc in TEST_CASES:
        for instance in tc['instances']:
            name = instance['name']

            try:
                # Run the check
                supervisor_check.check(instance)
            except Exception as e:
                if 'error_message' in tc:  # excepted error
                    assert str(e) == tc['error_message']
                else:
                    raise e
            else:
                expected_metrics = tc['expected_metrics'][name]
                for m in expected_metrics:
                    m_name = m[0]
                    m_value = m[1]
                    m_tags = m[2]['tags']
                    aggregator.assert_metric(m_name, value=m_value, tags=m_tags)

                # Assert that the check generated the right service checks
                expected_service_checks = tc['expected_service_checks'][name]
                for sc in expected_service_checks:
                    aggregator.assert_service_check(sc['check'], status=sc['status'], tags=sc['tags'])

                aggregator.reset()


def test_build_message():
    """Unit test supervisord build service check message."""
    time_stop = 0
    time_start = 1414815388
    time_now = 1414815513
    process = {
        'now': time_now,
        'group': 'mysql',
        'description': 'pid 787, uptime 0:02:05',
        'pid': 787,
        'stderr_logfile': '/var/log/supervisor/mysql-stderr---supervisor-3ATI82.log',
        'stop': time_stop,
        'statename': 'RUNNING',
        'start': time_start,
        'state': 20,
        'stdout_logfile': '/var/log/mysql/mysql.log',
        'logfile': '/var/log/mysql/mysql.log',
        'exitstatus': 0,
        'spawnerr': '',
        'name': 'mysql'
    }

    expected_message = """Current time: {time_now}
Process name: mysql
Process group: mysql
Description: pid 787, uptime 0:02:05
Error log file: /var/log/supervisor/mysql-stderr---supervisor-3ATI82.log
Stdout log file: /var/log/mysql/mysql.log
Log file: /var/log/mysql/mysql.log
State: RUNNING
Start time: {time_start}
Stop time: {time_stop}\nExit Status: 0""".format(
        time_now=FORMAT_TIME(time_now),
        time_start=FORMAT_TIME(time_start),
        time_stop='' if time_stop == 0 else FORMAT_TIME(time_stop)
    )

    assert expected_message == supervisor_check._build_message(process)


class MockXmlRcpServer:
    """Class that mocks an XML RPC server. Initialized using a mocked
     supervisord server url, which is used to initialize the supervisord
     server.
     """
    def __init__(self, url):
        self.supervisor = MockSupervisor(url)


class MockSupervisor:
    """Class that mocks a supervisord sever. Initialized using the server url
    and mocks process methods providing mocked process information for testing
    purposes.
    """
    MOCK_PROCESSES = {
        'http://localhost:9001/RPC2': [{
            'now': 1414815513,
            'group': 'mysql',
            'description': 'pid 787, uptime 0:02:05',
            'pid': 787,
            'stderr_logfile': '/var/log/supervisor/mysql-stderr---supervisor-3ATI82.log',
            'stop': 0,
            'statename': 'RUNNING',
            'start': 1414815388,
            'state': 20,
            'stdout_logfile': '/var/log/mysql/mysql.log',
            'logfile': '/var/log/mysql/mysql.log',
            'exitstatus': 0,
            'spawnerr': '',
            'name': 'mysql'
        }, {
            'now': 1414815738,
            'group': 'java',
            'description': 'Nov 01 04:22 AM',
            'pid': 0,
            'stderr_logfile': '/var/log/supervisor/java-stderr---supervisor-lSdcKZ.log',
            'stop': 1414815722,
            'statename': 'STOPPED',
            'start': 1414815388,
            'state': 0,
            'stdout_logfile': '/var/log/java/java.log',
            'logfile': '/var/log/java/java.log',
            'exitstatus': 21,
            'spawnerr': '',
            'name': 'java'
        }, {
            'now': 1414815738,
            'group': 'python',
            'description': '',
            'pid': 2765,
            'stderr_logfile': '/var/log/supervisor/python-stderr---supervisor-vFzxIg.log',
            'stop': 1414815737,
            'statename': 'STARTING',
            'start': 1414815737,
            'state': 10,
            'stdout_logfile': '/var/log/python/python.log',
            'logfile': '/var/log/python/python.log',
            'exitstatus': 0,
            'spawnerr': '',
            'name': 'python'
        }],
        'http://user:pass@localhost:9001/RPC2': [{
            'now': 1414869824,
            'group': 'apache2',
            'description': 'Exited too quickly (process log may have details)',
            'pid': 0,
            'stderr_logfile': '/var/log/supervisor/apache2-stderr---supervisor-0PkXWd.log',
            'stop': 1414867047,
            'statename': 'FATAL',
            'start': 1414867047,
            'state': 200,
            'stdout_logfile': '/var/log/apache2/apache2.log',
            'logfile': '/var/log/apache2/apache2.log',
            'exitstatus': 0,
            'spawnerr': 'Exited too quickly (process log may have details)',
            'name': 'apache2'
        }, {
            'now': 1414871104,
            'group': 'webapp',
            'description': '',
            'pid': 17600,
            'stderr_logfile': '/var/log/supervisor/webapp-stderr---supervisor-onZK__.log',
            'stop': 1414871101,
            'statename': 'STOPPING',
            'start': 1414871102,
            'state': 40,
            'stdout_logfile': '/var/log/company/webapp.log',
            'logfile': '/var/log/company/webapp.log',
            'exitstatus': 1,
            'spawnerr': '',
            'name': 'webapp'
        }],
        'http://10.60.130.82:9001/RPC2': [{
            'now': 1414871588,
            'group': 'ruby',
            'description': 'Exited too quickly (process log may have details)',
            'pid': 0,
            'stderr_logfile': '/var/log/supervisor/ruby-stderr---supervisor-BU7Wat.log',
            'stop': 1414871588,
            'statename': 'BACKOFF',
            'start': 1414871588,
            'state': 30,
            'stdout_logfile': '/var/log/ruby/ruby.log',
            'logfile': '/var/log/ruby/ruby.log',
            'exitstatus': 0,
            'spawnerr': 'Exited too quickly (process log may have details)',
            'name': 'ruby'
        }]
    }

    def __init__(self, url):
        self.url = url

    def getAllProcessInfo(self):
        self._validate_request()
        return self.MOCK_PROCESSES[self.url]

    def getProcessInfo(self, proc_name):
        self._validate_request(proc=proc_name)
        for proc in self.MOCK_PROCESSES[self.url]:
            if proc['name'] == proc_name:
                return proc
        raise Exception('Process not found: %s' % proc_name)

    def _validate_request(self, proc=None):
        '''Validates request and simulates errors when not valid'''
        if 'invalid_host' in self.url:
            # Simulate connecting to an invalid host/port in order to
            # raise `socket.error: [Errno 111] Connection refused`
            socket().connect(('localhost', 38837))
        elif 'invalid_pass' in self.url:
            # Simulate xmlrpc exception for invalid credentials
            raise xmlrpclib.ProtocolError(self.url[7:], 401,
                                          'Unauthorized', None)
        elif proc is not None and 'invalid' in proc:
            # Simulate xmlrpc exception for process not found
            raise xmlrpclib.Fault(10, 'BAD_NAME')
