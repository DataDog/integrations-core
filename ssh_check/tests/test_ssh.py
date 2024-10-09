# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import namedtuple
from copy import deepcopy

import paramiko
import pytest
from mock import MagicMock, call, create_autospec

from datadog_checks.ssh_check import CheckSSH

from . import common

pytestmark = pytest.mark.unit

# paramiko.SSHClient.connect returns None if the connection is successful.
# We use a variable with a descriptive name for clarity.
CONNECTION_SUCCEEDED = None


def _setup_check_with_mock_client(instance, connect_result):
    client = create_autospec(paramiko.SSHClient)
    client.connect.side_effect = [connect_result]
    client.get_transport.return_value = namedtuple('Transport', ['remote_version'])('SSH-2.0-OpenSSH_8.1')

    ssh = CheckSSH('ssh_check', {}, [instance])
    ssh.initialize_client = MagicMock(return_value=client)

    return client, ssh


def test_ssh(aggregator):
    instance = common.INSTANCES['main']
    client, check = _setup_check_with_mock_client(instance, connect_result=CONNECTION_SUCCEEDED)

    check.check({})

    for sc in aggregator.service_checks(CheckSSH.SSH_SERVICE_CHECK_NAME):
        assert sc.status == CheckSSH.OK
        for tag in sc.tags:
            assert tag in ('instance:io.netgarage.org-22', 'optional:tag1')

    assert client.connect.mock_calls == [
        call(
            instance['host'],
            port=instance['port'],
            username=instance['username'],
            password=instance['password'],
        ),
    ]
    # Make sure we close the client after the check is done.
    assert client.close.mock_calls == [call()]


@pytest.mark.parametrize(
    'instance_name, error, error_msg',
    [
        pytest.param(
            'bad_auth',
            paramiko.ssh_exception.NoValidConnectionsError(
                {
                    ('127.0.0.1', 22): ConnectionRefusedError(61, 'Connection refused'),
                    ('::1', 22, 0, 0): ConnectionRefusedError(61, 'Connection refused'),
                }
            ),
            'Unable to connect to port 22 on 127.0.0.1 or ::1',
            id='bad auth credentials',
        ),
        pytest.param(
            'bad_hostname', TimeoutError(0.5, 'Operation timed out'), 'Operation timed out', id='bad hostname'
        ),
    ],
)
def test_ssh_bad_config(aggregator, instance_name, error, error_msg):
    instance = common.INSTANCES[instance_name]
    client, check = _setup_check_with_mock_client(instance, connect_result=error)

    with pytest.raises(Exception, match=error_msg):
        check.check({})

    for sc in aggregator.service_checks(CheckSSH.SSH_SERVICE_CHECK_NAME):
        assert sc.status == CheckSSH.CRITICAL
    assert client.connect.mock_calls == [
        call(
            instance['host'],
            port=instance['port'],
            username=instance['username'],
            password=instance['password'],
        ),
    ]
    # Make sure we close the client after the check is done.
    assert client.close.mock_calls == [call()]


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
                'version.raw': 'OpenSSH_for_Windows_7.7p1, LibreSSL 2.6.5',
                'flavor': 'OpenSSH',
            },
        ),
        (
            'SSH-2.0-OpenSSH_8.1',
            {
                'version.major': '8',
                'version.minor': '1',
                'version.scheme': 'ssh_check',
                'version.raw': 'SSH-2.0-OpenSSH_8.1',
                'flavor': 'OpenSSH',
            },
        ),
        (
            'SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u2',
            {
                'version.major': '7',
                'version.minor': '4',
                'version.release': 'p1',
                'version.scheme': 'ssh_check',
                'version.raw': 'SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u2',
                'flavor': 'OpenSSH',
            },
        ),
    ],
)
def test_collect_metadata(version, metadata, datadog_agent):
    client = MagicMock()
    client.get_transport = MagicMock(return_value=namedtuple('Transport', ['remote_version'])(version))

    ssh = CheckSSH('ssh_check', {}, [common.INSTANCES['main']])
    ssh.check_id = 'test:123'
    ssh._collect_metadata(client)
    datadog_agent.assert_metadata('test:123', metadata)


def test_collect_bad_metadata(datadog_agent):
    client = MagicMock()
    client.get_transport = MagicMock(return_value=namedtuple('Transport', ['remote_version'])('Cannot parse this'))

    ssh = CheckSSH('ssh_check', {}, [common.INSTANCES['main']])
    ssh.check_id = 'test:123'
    ssh._collect_metadata(client)
    datadog_agent.assert_metadata_count(1)
    datadog_agent.assert_metadata('test:123', {'flavor': 'unknown'})


@pytest.mark.parametrize(
    'settings',
    [
        pytest.param({}, id='implicitly'),
        pytest.param({'force_sha1': False}, id='explicitly'),
    ],
)
def test_force_sha1_disabled(aggregator, dd_run_check, settings):
    inst = deepcopy(common.INSTANCES['main'])
    inst.update(settings)
    client, ssh = _setup_check_with_mock_client(inst, connect_result=paramiko.ssh_exception.AuthenticationException)

    with pytest.raises(Exception, match='AuthenticationException'):
        dd_run_check(ssh)

    aggregator.assert_service_check(CheckSSH.SSH_SERVICE_CHECK_NAME, CheckSSH.CRITICAL)
    assert client.connect.mock_calls == [
        call(
            ssh.instance['host'],
            port=ssh.instance['port'],
            username=ssh.instance['username'],
            password=ssh.instance['password'],
        )
    ]


def test_force_sha1_enabled(aggregator, dd_run_check):
    settings = {'force_sha1': True}
    inst = deepcopy(common.INSTANCES['main'])
    inst.update(settings)
    client, ssh = _setup_check_with_mock_client(inst, connect_result=CONNECTION_SUCCEEDED)

    dd_run_check(ssh)

    aggregator.assert_service_check(CheckSSH.SSH_SERVICE_CHECK_NAME, CheckSSH.OK)
    assert client.connect.mock_calls == [
        call(
            ssh.instance['host'],
            port=ssh.instance['port'],
            username=ssh.instance['username'],
            password=ssh.instance['password'],
            disabled_algorithms={'pubkeys': ['rsa-sha2-512', 'rsa-sha2-256']},
        ),
    ]
