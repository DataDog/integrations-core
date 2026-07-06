# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections import namedtuple
from copy import deepcopy

import mock
import paramiko
import pytest
from mock import create_autospec

from datadog_checks.dev import get_here
from datadog_checks.ssh_check import CheckSSH

from . import common
from .test_ssh import CONNECTION_SUCCEEDED, _setup_check_with_mock_client

pytestmark = pytest.mark.unit

# Real (encrypted) key file used to exercise the private-key-loading branches without mocking paramiko's own logic.
PRIVATE_KEY_FILE = os.path.join(get_here(), 'private_key')


def test_port_defaults_to_22():
    # Kills the core/NumberReplacer mutants at ssh_check.py:32 (port default 22 -> 23/21).
    ssh = CheckSSH('ssh_check', {}, [{'host': 'example.com', 'username': 'test'}])
    assert ssh.port == 22


def test_sftp_check_defaults_to_true():
    # Kills the core/ReplaceTrueWithFalse mutant at ssh_check.py:37 (sftp_check default True -> False).
    ssh = CheckSSH('ssh_check', {}, [{'host': 'example.com', 'username': 'test'}])
    assert ssh.sftp_check is True


def test_private_key_file_none_skips_key_loading():
    # Kills the core/ReplaceComparisonOperator_IsNot_Is and AddNot mutants at ssh_check.py:50.
    instance = {'host': 'example.com', 'username': 'test', 'password': 'pw'}
    client, ssh = _setup_check_with_mock_client(instance, connect_result=CONNECTION_SUCCEEDED, authentication_result=True)
    ssh.warning = mock.MagicMock()

    ssh.check({})

    ssh.warning.assert_not_called()


def test_private_key_file_set_without_password_warns_and_continues():
    # Kills the core/ReplaceComparisonOperator_IsNot_Is/AddNot mutants at ssh_check.py:50 and the
    # core/ExceptionReplacer mutant at ssh_check.py:58 (PasswordRequiredException swapped for an undefined name).
    instance = deepcopy(common.INSTANCES['main'])
    instance['private_key_file'] = PRIVATE_KEY_FILE
    instance['password'] = None
    client, ssh = _setup_check_with_mock_client(instance, connect_result=CONNECTION_SUCCEEDED, authentication_result=True)
    ssh.warning = mock.MagicMock()

    ssh.check({})

    ssh.warning.assert_called_once_with("Private key file is encrypted but no password was given")


def test_private_key_file_wrong_password_warns_and_continues():
    # Kills the core/ExceptionReplacer mutant at ssh_check.py:60 (SSHException swapped for an undefined name).
    instance = deepcopy(common.INSTANCES['main'])
    instance['private_key_file'] = PRIVATE_KEY_FILE
    instance['password'] = 'wrong-password'
    client, ssh = _setup_check_with_mock_client(instance, connect_result=CONNECTION_SUCCEEDED, authentication_result=True)
    ssh.warning = mock.MagicMock()

    ssh.check({})

    ssh.warning.assert_called_once_with("Private key file is invalid")


@pytest.mark.parametrize(
    'private_key_type, expected_ecdsa_calls, expected_rsa_calls',
    [
        # Built dynamically (not a literal) so it isn't the same interned string object as ssh_check.py's
        # 'ecdsa' literal, which would otherwise make the core/ReplaceComparisonOperator_Eq_Is mutant survive.
        pytest.param(''.join(['ec', 'dsa']), 1, 0, id='ecdsa'),
        pytest.param('aaa', 0, 1, id='lexicographically-below-ecdsa'),
        pytest.param('zzz', 0, 1, id='lexicographically-above-ecdsa'),
    ],
)
def test_private_key_type_selects_key_class(private_key_type, expected_ecdsa_calls, expected_rsa_calls):
    # Kills the core/ReplaceComparisonOperator_Eq_* and AddNot mutants at ssh_check.py:52.
    instance = deepcopy(common.INSTANCES['main'])
    instance['private_key_file'] = PRIVATE_KEY_FILE
    instance['private_key_type'] = private_key_type
    client, ssh = _setup_check_with_mock_client(instance, connect_result=CONNECTION_SUCCEEDED, authentication_result=True)

    with mock.patch('paramiko.ECDSAKey.from_private_key_file') as mock_ecdsa, mock.patch(
        'paramiko.RSAKey.from_private_key_file'
    ) as mock_rsa:
        ssh.check({})

    assert mock_ecdsa.call_count == expected_ecdsa_calls
    assert mock_rsa.call_count == expected_rsa_calls


@pytest.mark.parametrize(
    'add_missing_keys, should_set_policy',
    [
        pytest.param(True, True, id='enabled'),
        pytest.param(False, False, id='disabled (default)'),
    ],
)
def test_add_missing_keys_controls_host_key_policy(add_missing_keys, should_set_policy):
    # Kills the core/AddNot mutant at ssh_check.py:64 (`if self.add_missing_keys` negated).
    instance = deepcopy(common.INSTANCES['main'])
    instance['add_missing_keys'] = add_missing_keys
    client, ssh = _setup_check_with_mock_client(instance, connect_result=CONNECTION_SUCCEEDED, authentication_result=True)

    ssh.check({})

    assert client.set_missing_host_key_policy.called is should_set_policy


@pytest.mark.parametrize(
    'sftp_check, expects_sftp_service_check',
    [
        pytest.param(True, True, id='enabled'),
        pytest.param(False, False, id='disabled'),
    ],
)
def test_sftp_service_check_reported_on_connect_failure(aggregator, sftp_check, expects_sftp_service_check):
    # Kills the core/AddNot mutant at ssh_check.py:103 (`if self.sftp_check` negated).
    instance = deepcopy(common.INSTANCES['main'])
    instance['sftp_check'] = sftp_check
    client, ssh = _setup_check_with_mock_client(
        instance, connect_result=ConnectionRefusedError(61, 'Connection refused'), authentication_result=False
    )

    with pytest.raises(Exception):
        ssh.check({})

    sftp_checks = aggregator.service_checks(CheckSSH.SFTP_SERVICE_CHECK_NAME)
    assert (len(sftp_checks) == 1) is expects_sftp_service_check


@pytest.mark.parametrize(
    'sftp_check, expects_sftp_activity',
    [
        pytest.param(True, True, id='enabled'),
        pytest.param(False, False, id='disabled'),
    ],
)
def test_sftp_session_opened_only_when_sftp_check_enabled(aggregator, sftp_check, expects_sftp_activity):
    # Kills the core/AddNot mutant at ssh_check.py:112 (`if self.sftp_check` negated).
    instance = deepcopy(common.INSTANCES['main'])
    instance['sftp_check'] = sftp_check
    client, ssh = _setup_check_with_mock_client(instance, connect_result=CONNECTION_SUCCEEDED, authentication_result=True)

    ssh.check({})

    assert client.open_sftp.called is expects_sftp_activity
    assert (len(aggregator.service_checks(CheckSSH.SFTP_SERVICE_CHECK_NAME)) == 1) is expects_sftp_activity


def test_sftp_response_time_is_end_minus_start(aggregator):
    # Kills the core/ReplaceBinaryOperator_Sub_* mutants at ssh_check.py:120 (end_time - start_time).
    instance = deepcopy(common.INSTANCES['main'])
    instance['sftp_check'] = True
    client, ssh = _setup_check_with_mock_client(instance, connect_result=CONNECTION_SUCCEEDED, authentication_result=True)

    with mock.patch('datadog_checks.ssh_check.ssh_check.time.time', side_effect=[10.0, 25.0]):
        ssh.check({})

    # 25.0 - 10.0 == 15.0, distinct from every other binary operator result (e.g. 25.0 % 10.0 == 5.0).
    aggregator.assert_metric('sftp.response_time', value=15.0, tags=ssh.base_tags)


def test_sftp_exception_reported_as_critical_with_message(aggregator):
    # Kills the core/ExceptionReplacer mutant at ssh_check.py:123 (Exception swapped for an undefined name) and the
    # core/ReplaceComparisonOperator_Is_GtE mutant at ssh_check.py:127 (status is AgentCheck.OK).
    instance = deepcopy(common.INSTANCES['main'])
    instance['sftp_check'] = True
    client, ssh = _setup_check_with_mock_client(instance, connect_result=CONNECTION_SUCCEEDED, authentication_result=True)
    client.open_sftp.side_effect = IOError('sftp unavailable')

    ssh.check({})

    sftp_checks = aggregator.service_checks(CheckSSH.SFTP_SERVICE_CHECK_NAME)
    assert sftp_checks[-1].status == CheckSSH.CRITICAL
    assert sftp_checks[-1].message == 'sftp unavailable'


def test_sftp_message_cleared_on_success(aggregator):
    # Kills the core/ReplaceComparisonOperator_Is_* and AddNot mutants at ssh_check.py:127 (status is AgentCheck.OK):
    # the aggregator stub raises if a service check is submitted as OK with a non-empty message.
    instance = deepcopy(common.INSTANCES['main'])
    instance['sftp_check'] = True
    client, ssh = _setup_check_with_mock_client(instance, connect_result=CONNECTION_SUCCEEDED, authentication_result=True)

    ssh.check({})

    aggregator.assert_service_check(CheckSSH.SFTP_SERVICE_CHECK_NAME, CheckSSH.OK)


def test_force_sha1_disabled_by_default():
    # Kills the core/AddNot mutant at ssh_check.py:43 (`if is_affirmative(...)` negated).
    ssh = CheckSSH('ssh_check', {}, [{'host': 'example.com', 'username': 'test'}])
    assert ssh._connection_settings_to_force_sha1 == {}


def test_force_sha1_enabled_sets_disabled_algorithms():
    # Kills the core/AddNot mutant at ssh_check.py:43 (`if is_affirmative(...)` negated).
    ssh = CheckSSH('ssh_check', {}, [{'host': 'example.com', 'username': 'test', 'force_sha1': True}])
    assert ssh._connection_settings_to_force_sha1 == {
        'disabled_algorithms': {'pubkeys': ['rsa-sha2-512', 'rsa-sha2-256']}
    }


def test_connect_uses_password_kwarg_when_no_private_key():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and AddNot mutants at ssh_check.py:72
    # (`if private_key is None` controls password vs. passphrase/pkey connect kwargs).
    instance = {'host': 'example.com', 'username': 'test', 'password': 'secret'}
    client, ssh = _setup_check_with_mock_client(instance, connect_result=CONNECTION_SUCCEEDED, authentication_result=True)

    ssh.check({})

    assert client.connect.call_args.kwargs['password'] == 'secret'
    assert 'passphrase' not in client.connect.call_args.kwargs
    assert 'pkey' not in client.connect.call_args.kwargs


def test_connect_uses_pkey_kwarg_when_private_key_present():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and AddNot mutants at ssh_check.py:72.
    instance = deepcopy(common.INSTANCES['main'])
    instance['private_key_file'] = PRIVATE_KEY_FILE
    instance['password'] = 'a-passphrase'
    client, ssh = _setup_check_with_mock_client(instance, connect_result=CONNECTION_SUCCEEDED, authentication_result=True)
    sentinel_key = object()

    with mock.patch('paramiko.RSAKey.from_private_key_file', return_value=sentinel_key):
        ssh.check({})

    assert client.connect.call_args.kwargs['pkey'] is sentinel_key
    assert client.connect.call_args.kwargs['passphrase'] == 'a-passphrase'
    assert 'password' not in client.connect.call_args.kwargs


def test_transport_none_reports_ssh_critical(aggregator):
    # Kills the core/ReplaceComparisonOperator_IsNot_Is and AddNot mutants at ssh_check.py:85
    # (`if transport is not None`).
    instance = deepcopy(common.INSTANCES['main'])
    client = create_autospec(paramiko.SSHClient)
    client.connect.side_effect = [CONNECTION_SUCCEEDED]
    client.get_transport.return_value = None
    ssh = CheckSSH('ssh_check', {}, [instance])
    ssh.initialize_client = mock.MagicMock(return_value=client)

    ssh.check({})

    aggregator.assert_service_check(CheckSSH.SSH_SERVICE_CHECK_NAME, CheckSSH.CRITICAL)


@pytest.mark.parametrize(
    'authenticated, service_check_result',
    [
        pytest.param(True, CheckSSH.OK, id='authenticated'),
        pytest.param(False, CheckSSH.CRITICAL, id='not authenticated'),
    ],
)
def test_transport_authenticated_controls_ssh_service_check(aggregator, authenticated, service_check_result):
    # Kills the core/AddNot mutant at ssh_check.py:86 (`if transport.is_authenticated()` negated).
    instance = deepcopy(common.INSTANCES['main'])
    client, ssh = _setup_check_with_mock_client(
        instance, connect_result=CONNECTION_SUCCEEDED, authentication_result=authenticated
    )

    ssh.check({})

    aggregator.assert_service_check(CheckSSH.SSH_SERVICE_CHECK_NAME, service_check_result)


def test_collect_metadata_flavor_openssh_when_present(datadog_agent):
    # Kills the core/AddNot mutant at ssh_check.py:149 (`if 'OpenSSH' in version` negated).
    client = mock.MagicMock()
    client.get_transport.return_value = namedtuple('Transport', ['remote_version'])('SSH-2.0-OpenSSH_8.1')

    ssh = CheckSSH('ssh_check', {}, [common.INSTANCES['main']])
    ssh.check_id = 'test:123'
    ssh._collect_metadata(client)

    datadog_agent.assert_metadata('test:123', {'flavor': 'OpenSSH'})


def test_collect_metadata_flavor_unknown_when_absent(datadog_agent):
    # Kills the core/AddNot mutant at ssh_check.py:149 (`if 'OpenSSH' in version` negated).
    client = mock.MagicMock()
    client.get_transport.return_value = namedtuple('Transport', ['remote_version'])('SomeOtherServer_1.0')

    ssh = CheckSSH('ssh_check', {}, [common.INSTANCES['main']])
    ssh.check_id = 'test:123'
    ssh._collect_metadata(client)

    datadog_agent.assert_metadata('test:123', {'flavor': 'unknown'})


def test_collect_metadata_handles_get_transport_exception(datadog_agent):
    # Kills the core/ExceptionReplacer mutant at ssh_check.py:145 (Exception swapped for an undefined name).
    client = mock.MagicMock()
    client.get_transport.side_effect = Exception("boom")

    ssh = CheckSSH('ssh_check', {}, [common.INSTANCES['main']])
    ssh.check_id = 'test:123'
    ssh._collect_metadata(client)

    datadog_agent.assert_metadata_count(0)
