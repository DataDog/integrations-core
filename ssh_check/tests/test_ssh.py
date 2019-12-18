# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading
from collections import namedtuple

import mock
import pytest
from mock import MagicMock

from datadog_checks.ssh_check import CheckSSH

from . import common

pytestmark = pytest.mark.unit


def test_ssh(aggregator):
    c = CheckSSH('ssh_check', {}, {}, list(common.INSTANCES.values()))

    nb_threads = threading.active_count()

    c.check(common.INSTANCES['main'])

    for sc in aggregator.service_checks(CheckSSH.SSH_SERVICE_CHECK_NAME):
        assert sc.status == CheckSSH.OK
        for tag in sc.tags:
            assert tag in ('instance:io.netgarage.org-22', 'optional:tag1')

    # Check that we've closed all connections, if not we're leaking threads
    common.wait_for_threads()
    assert nb_threads == threading.active_count()


def test_ssh_bad_config(aggregator):
    c = CheckSSH('ssh_check', {}, {}, list(common.INSTANCES.values()))

    nb_threads = threading.active_count()

    with pytest.raises(Exception):
        c.check(common.INSTANCES['bad_auth'])

    with pytest.raises(Exception):
        c.check(common.INSTANCES['bad_hostname'])

    for sc in aggregator.service_checks(CheckSSH.SSH_SERVICE_CHECK_NAME):
        assert sc.status == CheckSSH.CRITICAL

    # Check that we've closed all connections, if not we're leaking threads
    common.wait_for_threads()
    assert nb_threads == threading.active_count()


@pytest.mark.parametrize(
    'version, metadata',
    [
        (
            'OpenSSH_for_Windows_7.7p1, LibreSSL 2.6.5',
            {
                'version.major': '7',
                'version.minor': '7',
                'version.release': 'p1',
                'version.scheme': 'ssh_check',
                'flavor': 'OpenSSH',
            },
        ),
        (
            'SSH-2.0-OpenSSH_8.1',
            {'version.major': '8', 'version.minor': '1', 'version.scheme': 'ssh_check', 'flavor': 'OpenSSH'},
        ),
        (
            'SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u2',
            {
                'version.major': '7',
                'version.minor': '4',
                'version.release': 'p1',
                'version.scheme': 'ssh_check',
                'flavor': 'OpenSSH',
            },
        ),
    ],
)
def test_collect_metadata(version, metadata):
    client = MagicMock()
    client.get_transport = MagicMock(return_value=namedtuple('Transport', ['remote_version'])(version))

    ssh = CheckSSH('ssh_check', {}, {}, list(common.INSTANCES.values()))
    ssh.check_id = 'test:123'
    with mock.patch('datadog_checks.base.stubs.datadog_agent.set_check_metadata') as m:
        ssh._collect_metadata(client)
        for key, value in metadata.items():
            m.assert_any_call('test:123', key, value)
