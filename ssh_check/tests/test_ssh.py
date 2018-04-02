# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading

import pytest
from datadog_checks.stubs import aggregator

from datadog_checks.ssh_check import CheckSSH


@pytest.fixture
def Aggregator():
    aggregator.reset()
    return aggregator


class TestSshCheck:
    INSTANCES = {
        'main': {
            'host': 'io.netgarage.org',
            'port': 22,
            'username': 'level1',
            'password': 'level1',
            'sftp_check': False,
            'private_key_file': '',
            'add_missing_keys': True,
            'tags': ['optional:tag1']
        },
        'bad_auth': {
            'host': 'localhost',
            'port': 22,
            'username': 'test',
            'password': 'yodawg',
            'sftp_check': False,
            'private_key_file': '',
            'add_missing_keys': True
        },
        'bad_hostname': {
            'host': 'wronghost',
            'port': 22,
            'username': 'datadog01',
            'password': 'abcd',
            'sftp_check': False,
            'private_key_file': '',
            'add_missing_keys': True
        },
    }

    def test_check(self, Aggregator):
        c = CheckSSH('ssh_check', {}, {}, list(self.INSTANCES.values()))

        with pytest.raises(Exception):
            c.check(self.INSTANCES['bad_auth'])

        with pytest.raises(Exception):
            c.check(self.INSTANCES['bad_auth'])

        nb_threads = threading.active_count()

        # Testing that connection will work
        c.check(self.INSTANCES['main'])

        service = self.check.get_service_checks()
        self.assertEqual(service[0].get('status'), AgentCheck.OK)
        self.assertEqual(service[0].get('message'), "No errors occured")
        self.assertEqual(service[0].get('tags'), ["instance:io.netgarage.org-22", "optional:tag1"])

        service_fail = self.check.get_service_checks()
        # Check failure status
        self.assertEqual(service_fail[0].get('status'), AgentCheck.CRITICAL)
        # Check that we've closed all connections, if not we're leaking threads
        self.assertEqual(nb_threads, threading.active_count())
