# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest
import requests_kerberos

from datadog_checks.base import ConfigurationError
from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev import EnvVars
from datadog_checks.dev.http import MockResponse

pytestmark = [pytest.mark.unit]


def test_config_kerberos_legacy():
    instance = {'kerberos_auth': 'required'}
    init_config = {}

    # Trigger lazy import
    http = RequestsWrapper(instance, init_config)
    assert isinstance(http.options['auth'], requests_kerberos.HTTPKerberosAuth)

    with mock.patch('datadog_checks.base.utils.http.requests_kerberos.HTTPKerberosAuth') as m:
        RequestsWrapper(instance, init_config)

        m.assert_called_once_with(
            mutual_authentication=requests_kerberos.REQUIRED,
            delegate=False,
            force_preemptive=False,
            hostname_override=None,
            principal=None,
        )


def test_config_kerberos():
    instance = {'auth_type': 'kerberos', 'kerberos_auth': 'required'}
    init_config = {}

    # Trigger lazy import
    http = RequestsWrapper(instance, init_config)
    assert isinstance(http.options['auth'], requests_kerberos.HTTPKerberosAuth)

    with mock.patch('datadog_checks.base.utils.http.requests_kerberos.HTTPKerberosAuth') as m:
        RequestsWrapper(instance, init_config)

        m.assert_called_once_with(
            mutual_authentication=requests_kerberos.REQUIRED,
            delegate=False,
            force_preemptive=False,
            hostname_override=None,
            principal=None,
        )

    with mock.patch('datadog_checks.base.utils.http.requests_kerberos.HTTPKerberosAuth') as m:
        RequestsWrapper({'auth_type': 'kerberos', 'kerberos_auth': 'optional'}, init_config)

        m.assert_called_once_with(
            mutual_authentication=requests_kerberos.OPTIONAL,
            delegate=False,
            force_preemptive=False,
            hostname_override=None,
            principal=None,
        )

    with mock.patch('datadog_checks.base.utils.http.requests_kerberos.HTTPKerberosAuth') as m:
        RequestsWrapper({'auth_type': 'kerberos', 'kerberos_auth': 'disabled'}, init_config)

        m.assert_called_once_with(
            mutual_authentication=requests_kerberos.DISABLED,
            delegate=False,
            force_preemptive=False,
            hostname_override=None,
            principal=None,
        )


def test_config_kerberos_shortcut():
    instance = {'auth_type': 'kerberos', 'kerberos_auth': True}
    init_config = {}

    # Trigger lazy import
    http = RequestsWrapper(instance, init_config)
    assert isinstance(http.options['auth'], requests_kerberos.HTTPKerberosAuth)

    with mock.patch('datadog_checks.base.utils.http.requests_kerberos.HTTPKerberosAuth') as m:
        RequestsWrapper(instance, init_config)

        m.assert_called_once_with(
            mutual_authentication=requests_kerberos.REQUIRED,
            delegate=False,
            force_preemptive=False,
            hostname_override=None,
            principal=None,
        )


def test_config_kerberos_unknown():
    instance = {'auth_type': 'kerberos', 'kerberos_auth': 'unknown'}
    init_config = {}

    with pytest.raises(ConfigurationError):
        RequestsWrapper(instance, init_config)


def test_config_kerberos_keytab_file():
    instance = {'auth_type': 'kerberos', 'kerberos_keytab': '/test/file'}
    init_config = {}

    http = RequestsWrapper(instance, init_config)

    assert os.environ.get('KRB5_CLIENT_KTNAME') is None

    with mock.patch(
        'requests.get', side_effect=lambda *args, **kwargs: MockResponse(os.environ.get('KRB5_CLIENT_KTNAME', ''))
    ):
        response = http.get('https://www.google.com')
        assert response.text == '/test/file'

    assert os.environ.get('KRB5_CLIENT_KTNAME') is None


def test_config_kerberos_cache():
    instance = {'auth_type': 'kerberos', 'kerberos_cache': '/test/file'}
    init_config = {}

    http = RequestsWrapper(instance, init_config)

    assert os.environ.get('KRB5CCNAME') is None

    with mock.patch('requests.get', side_effect=lambda *args, **kwargs: MockResponse(os.environ.get('KRB5CCNAME', ''))):
        response = http.get('https://www.google.com')
        assert response.text == '/test/file'

    assert os.environ.get('KRB5CCNAME') is None


def test_config_kerberos_cache_restores_rollback():
    instance = {'auth_type': 'kerberos', 'kerberos_cache': '/test/file'}
    init_config = {}

    http = RequestsWrapper(instance, init_config)

    with EnvVars({'KRB5CCNAME': 'old'}):
        with mock.patch(
            'requests.get', side_effect=lambda *args, **kwargs: MockResponse(os.environ.get('KRB5CCNAME', ''))
        ):
            response = http.get('https://www.google.com')
            assert response.text == '/test/file'

        assert os.environ.get('KRB5CCNAME') == 'old'


def test_config_kerberos_keytab_file_rollback():
    instance = {'auth_type': 'kerberos', 'kerberos_keytab': '/test/file'}
    init_config = {}

    http = RequestsWrapper(instance, init_config)

    with EnvVars({'KRB5_CLIENT_KTNAME': 'old'}):
        assert os.environ.get('KRB5_CLIENT_KTNAME') == 'old'

        with mock.patch(
            'requests.get',
            side_effect=lambda *args, **kwargs: MockResponse(os.environ.get('KRB5_CLIENT_KTNAME', '')),
        ):
            response = http.get('https://www.google.com')
            assert response.text == '/test/file'

        assert os.environ.get('KRB5_CLIENT_KTNAME') == 'old'


def test_config_kerberos_legacy_remap():
    instance = {'auth_type': 'kerberos', 'kerberos': True}
    init_config = {}

    # Trigger lazy import
    http = RequestsWrapper(instance, init_config)
    assert isinstance(http.options['auth'], requests_kerberos.HTTPKerberosAuth)

    with mock.patch('datadog_checks.base.utils.http.requests_kerberos.HTTPKerberosAuth') as m:
        RequestsWrapper(instance, init_config)

        m.assert_called_once_with(
            mutual_authentication=requests_kerberos.REQUIRED,
            delegate=False,
            force_preemptive=False,
            hostname_override=None,
            principal=None,
        )
