# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading

import pytest

from datadog_checks.ssh_check import CheckSSH


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
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

    def test_ssh(self, aggregator):
        c = CheckSSH('ssh_check', {}, {}, list(self.INSTANCES.values()))

        nb_threads = threading.active_count()

        c.check(self.INSTANCES['main'])

        for sc in aggregator.service_checks(CheckSSH.SSH_SERVICE_CHECK_NAME):
            assert sc.status == CheckSSH.OK
            for tag in sc.tags:
                assert tag in ('instance:io.netgarage.org-22', 'optional:tag1')

        # Check that we've closed all connections, if not we're leaking threads
        assert nb_threads == threading.active_count()

    def test_ssh_bad_config(self, aggregator):
        c = CheckSSH('ssh_check', {}, {}, list(self.INSTANCES.values()))

        nb_threads = threading.active_count()

        with pytest.raises(Exception):
            c.check(self.INSTANCES['bad_auth'])

        with pytest.raises(Exception):
            c.check(self.INSTANCES['bad_hostname'])

        for sc in aggregator.service_checks(CheckSSH.SSH_SERVICE_CHECK_NAME):
            assert sc.status == CheckSSH.CRITICAL

        # Check that we've closed all connections, if not we're leaking threads
        assert nb_threads == threading.active_count()
