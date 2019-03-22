# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading

THREAD_TIMEOUT = 10

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

INSTANCE_INTEGRATION = {
    "host": "127.0.0.1",
    "port": 8022,
    "password": "secured_password",
    "username": "root",
    "add_missing_keys": True,
}


def wait_for_threads():
    for thread in threading.enumerate():
        try:
            thread.join(THREAD_TIMEOUT)
        except RuntimeError:
            pass
