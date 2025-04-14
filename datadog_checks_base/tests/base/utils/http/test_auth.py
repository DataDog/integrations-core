# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
import requests_ntlm
from aws_requests_auth import boto_utils as requests_aws
from requests import auth as requests_auth

from datadog_checks.base import ConfigurationError
from datadog_checks.base.utils.http import RequestsWrapper

pytestmark = [pytest.mark.unit]


def test_config_default():
    instance = {}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.options['auth'] is None


def test_config_basic():
    instance = {'username': 'user', 'password': 'pass'}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.options['auth'] == ('user', 'pass')


def test_config_basic_authtype():
    instance = {'username': 'user', 'password': 'pass', 'auth_type': 'basic'}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.options['auth'] == ('user', 'pass')


def test_config_basic_no_legacy_encoding():
    instance = {'username': 'user', 'password': 'pass', 'use_legacy_auth_encoding': False}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.options['auth'] == (b'user', b'pass')


def test_config_digest_authtype():
    instance = {'username': 'user', 'password': 'pass', 'auth_type': 'digest'}
    init_config = {}
    http = RequestsWrapper(instance, init_config)
    assert isinstance(http.options['auth'], requests_auth.HTTPDigestAuth)

    with mock.patch('datadog_checks.base.utils.http.requests_auth.HTTPDigestAuth') as m:
        RequestsWrapper(instance, init_config)

        m.assert_called_once_with('user', 'pass')


def test_config_basic_only_username():
    instance = {'username': 'user'}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.options['auth'] is None


def test_config_basic_only_password():
    instance = {'password': 'pass'}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.options['auth'] is None


@pytest.mark.parametrize('username,password', [('user', ''), ('', 'pass'), ('', '')])
def test_config_basic_allows_empty_strings(username, password):
    instance = {'username': username, 'password': password}
    init_config = {}
    http = RequestsWrapper(instance, init_config)

    assert http.options['auth'] == (username, password)


def test_config_ntlm():
    instance = {'auth_type': 'ntlm', 'ntlm_domain': 'domain\\user', 'password': 'pass'}
    init_config = {}

    # Trigger lazy import
    http = RequestsWrapper(instance, init_config)
    assert isinstance(http.options['auth'], requests_ntlm.HttpNtlmAuth)

    with mock.patch('datadog_checks.base.utils.http.requests_ntlm.HttpNtlmAuth') as m:
        RequestsWrapper(instance, init_config)

        m.assert_called_once_with('domain\\user', 'pass')


def test_config_ntlm_legacy(caplog):
    instance = {'ntlm_domain': 'domain\\user', 'password': 'pass'}
    init_config = {}

    # Trigger lazy import
    http = RequestsWrapper(instance, init_config)
    assert isinstance(http.options['auth'], requests_ntlm.HttpNtlmAuth)

    with mock.patch('datadog_checks.base.utils.http.requests_ntlm.HttpNtlmAuth') as m:
        RequestsWrapper(instance, init_config)

        m.assert_called_once_with('domain\\user', 'pass')

    assert (
        'The ability to use NTLM auth without explicitly setting auth_type to '
        '`ntlm` is deprecated and will be removed in Agent 8'
    ) in caplog.text


def test_config_aws():
    instance = {'auth_type': 'aws', 'aws_host': 'uri', 'aws_region': 'earth', 'aws_service': 'saas'}
    init_config = {}

    # Trigger lazy import
    http = RequestsWrapper(instance, init_config)
    assert isinstance(http.options['auth'], requests_aws.BotoAWSRequestsAuth)

    with mock.patch('datadog_checks.base.utils.http.requests_aws.BotoAWSRequestsAuth') as m:
        RequestsWrapper(instance, init_config)

        m.assert_called_once_with(aws_host='uri', aws_region='earth', aws_service='saas')


def test_config_aws_service_remapper():
    instance = {'auth_type': 'aws', 'aws_region': 'us-east-1'}
    init_config = {}
    remapper = {
        'aws_service': {'name': 'aws_service', 'default': 'es'},
        'aws_host': {'name': 'aws_host', 'default': 'uri'},
    }

    with mock.patch('datadog_checks.base.utils.http.requests_aws.BotoAWSRequestsAuth') as m:
        RequestsWrapper(instance, init_config, remapper)

        m.assert_called_once_with(aws_host='uri', aws_region='us-east-1', aws_service='es')


@pytest.mark.parametrize(
    'case, instance, match',
    [
        ('no host', {'auth_type': 'aws'}, '^AWS auth requires the setting `aws_host`$'),
        ('no region', {'auth_type': 'aws', 'aws_host': 'uri'}, '^AWS auth requires the setting `aws_region`$'),
        (
            'no service',
            {'auth_type': 'aws', 'aws_host': 'uri', 'aws_region': 'us-east-1'},
            '^AWS auth requires the setting `aws_service`$',
        ),
        ('empty host', {'auth_type': 'aws', 'aws_host': ''}, '^AWS auth requires the setting `aws_host`$'),
        (
            'empty region',
            {'auth_type': 'aws', 'aws_host': 'uri', 'aws_region': ''},
            '^AWS auth requires the setting `aws_region`$',
        ),
        (
            'empty service',
            {'auth_type': 'aws', 'aws_host': 'uri', 'aws_region': 'us-east-1', 'aws_service': ''},
            '^AWS auth requires the setting `aws_service`$',
        ),
    ],
)
def test_config_aws_invalid_cases(case, instance, match):
    init_config = {}
    with pytest.raises(ConfigurationError, match=match):
        RequestsWrapper(instance, init_config)
