# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import namedtuple
from copy import deepcopy

import paramiko
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from mock import MagicMock, call, create_autospec

from datadog_checks.ssh_check import CheckSSH

from . import common

pytestmark = pytest.mark.unit

# paramiko.SSHClient.connect returns None if the connection is successful.
# We use a variable with a descriptive name for clarity.
CONNECTION_SUCCEEDED = None


def _setup_check_with_mock_client(instance, connect_result, authentication_result):
    mock_transport = MagicMock()
    mock_transport.remote_version = 'SSH-2.0-OpenSSH_8.1'
    mock_transport.is_authenticated.return_value = authentication_result

    client = create_autospec(paramiko.SSHClient)
    client.connect.side_effect = [connect_result]

    client.get_transport.return_value = mock_transport

    ssh = CheckSSH('ssh_check', {}, [instance])
    ssh.initialize_client = MagicMock(return_value=client)

    return client, ssh


@pytest.mark.parametrize(
    'authenticated,service_check_result',
    [
        pytest.param(True, CheckSSH.OK, id='authenticated'),
        pytest.param(False, CheckSSH.CRITICAL, id='not authenticated'),
    ],
)
def test_ssh(aggregator, authenticated, service_check_result):
    instance = common.INSTANCES['main']
    client, check = _setup_check_with_mock_client(
        instance, connect_result=CONNECTION_SUCCEEDED, authentication_result=authenticated
    )

    check.check({})

    for sc in aggregator.service_checks(CheckSSH.SSH_SERVICE_CHECK_NAME):
        assert sc.status == service_check_result
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
    client, check = _setup_check_with_mock_client(instance, connect_result=error, authentication_result=False)

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
    client, ssh = _setup_check_with_mock_client(
        inst, connect_result=paramiko.ssh_exception.AuthenticationException, authentication_result=False
    )

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


def _write_private_key(path, private_key):
    path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH, serialization.NoEncryption()
        )
    )
    return str(path)


@pytest.mark.parametrize(
    'private_key_type, private_key, expected_class',
    [
        pytest.param('rsa', rsa.generate_private_key(65537, 2048), paramiko.RSAKey, id='rsa'),
        pytest.param('ecdsa', ec.generate_private_key(ec.SECP256R1()), paramiko.ECDSAKey, id='ecdsa'),
        pytest.param('ed25519', ed25519.Ed25519PrivateKey.generate(), paramiko.Ed25519Key, id='ed25519'),
        pytest.param('ED25519', ed25519.Ed25519PrivateKey.generate(), paramiko.Ed25519Key, id='case insensitive'),
        # Unknown types have always been loaded as RSA.
        pytest.param('unknown', rsa.generate_private_key(65537, 2048), paramiko.RSAKey, id='unknown falls back to rsa'),
    ],
)
def test_private_key_type(dd_run_check, tmp_path, private_key_type, private_key, expected_class):
    inst = deepcopy(common.INSTANCES['main'])
    inst['private_key_file'] = _write_private_key(tmp_path / 'id_key', private_key)
    inst['private_key_type'] = private_key_type
    client, ssh = _setup_check_with_mock_client(inst, connect_result=CONNECTION_SUCCEEDED, authentication_result=True)

    dd_run_check(ssh)

    # A key that fails to load makes the check silently fall back to password authentication.
    assert isinstance(client.connect.call_args.kwargs.get('pkey'), expected_class)


def test_force_sha1_enabled(aggregator, dd_run_check):
    settings = {'force_sha1': True}
    inst = deepcopy(common.INSTANCES['main'])
    inst.update(settings)
    client, ssh = _setup_check_with_mock_client(inst, connect_result=CONNECTION_SUCCEEDED, authentication_result=True)

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
