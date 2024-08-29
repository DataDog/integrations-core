# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import threading

from datadog_checks.ssh_check import CheckSSH

THREAD_TIMEOUT = 10

SSH_SERVER_IMAGE = os.environ['SSH_SERVER_IMAGE']
SSH_SERVER_VERSION = os.environ.get('SSH_SERVER_VERSION')

INSTANCES = {
    'main': {
        'host': 'io.netgarage.org',
        'port': 22,
        'username': 'level1',
        'password': 'level1',
        'sftp_check': False,
        'private_key_file': '',
        'add_missing_keys': True,
        'tags': ['optional:tag1'],
    },
    'bad_auth': {
        'host': 'localhost',
        'port': 22,
        'username': 'test',
        'password': 'yodawg',
        'sftp_check': False,
        'private_key_file': '',
        'add_missing_keys': True,
    },
    'bad_hostname': {
        'host': 'bad.example.com',
        'port': 22,
        'username': 'datadog01',
        'password': 'abcd',
        'sftp_check': False,
        'private_key_file': '',
        'add_missing_keys': True,
    },
}

INSTANCE_INTEGRATION = {
    "host": "127.0.0.1",
    "port": 8022,
    "password": "secured_password",
    "username": "root",
    "add_missing_keys": True,
}


def wait_for_threads():
    for thread in threading.enumerate():
        # We skip the dummy threads since they can't be joined
        if isinstance(thread, threading._DummyThread):
            continue
        else:
            try:
                thread.join(THREAD_TIMEOUT)
            except RuntimeError:
                pass


def _test_check(aggregator, instance):
    expected_tags = ["instance:{}-{}".format(instance.get("host"), instance.get("port", 22))]
    aggregator.assert_metric("sftp.response_time", tags=expected_tags)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check(CheckSSH.SSH_SERVICE_CHECK_NAME, CheckSSH.OK)
