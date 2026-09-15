# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections.abc import Mapping
from typing import Any

import mock
import pytest
import requests
import requests_kerberos

from datadog_checks.base import ConfigurationError
from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev import EnvVars

from .common import RequestsTransport

pytestmark = [pytest.mark.unit]


class EnvironmentRecordingTransport(RequestsTransport):
    def __init__(self, variable: str) -> None:
        super().__init__()
        self.variable = variable
        self.values: list[str | None] = []

    def send(
        self,
        request: requests.PreparedRequest,
        stream: bool = False,
        timeout: Any = None,
        verify: bool | str = True,
        cert: Any = None,
        proxies: Mapping[str, str] | None = None,
    ) -> requests.Response:
        self.values.append(os.environ.get(self.variable))
        return super().send(request, stream=stream, timeout=timeout, verify=verify, cert=cert, proxies=proxies)


def _create_requests_client(instance: dict[str, object], transport: RequestsTransport) -> RequestsWrapper:
    session = requests.Session()
    session.mount('http://', transport)
    http = RequestsWrapper(instance, {}, session=session)
    http.persist_connections = True
    return http


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
    instance = {'auth_type': 'kerberos', 'kerberos_auth': 'disabled', 'kerberos_keytab': '/test/file'}
    transport = EnvironmentRecordingTransport('KRB5_CLIENT_KTNAME')
    transport.respond()
    http = _create_requests_client(instance, transport)

    assert os.environ.get('KRB5_CLIENT_KTNAME') is None

    response = http.get('http://www.google.com')

    assert response.status_code == 200
    assert transport.values == ['/test/file']
    assert os.environ.get('KRB5_CLIENT_KTNAME') is None


def test_config_kerberos_cache():
    instance = {'auth_type': 'kerberos', 'kerberos_auth': 'disabled', 'kerberos_cache': '/test/file'}
    transport = EnvironmentRecordingTransport('KRB5CCNAME')
    transport.respond()
    http = _create_requests_client(instance, transport)

    assert os.environ.get('KRB5CCNAME') is None

    response = http.get('http://www.google.com')

    assert response.status_code == 200
    assert transport.values == ['/test/file']
    assert os.environ.get('KRB5CCNAME') is None


def test_config_kerberos_cache_restores_rollback():
    instance = {'auth_type': 'kerberos', 'kerberos_auth': 'disabled', 'kerberos_cache': '/test/file'}
    transport = EnvironmentRecordingTransport('KRB5CCNAME')
    transport.respond()
    http = _create_requests_client(instance, transport)

    with EnvVars({'KRB5CCNAME': 'old'}):
        response = http.get('http://www.google.com')

        assert response.status_code == 200
        assert transport.values == ['/test/file']
        assert os.environ.get('KRB5CCNAME') == 'old'


def test_config_kerberos_keytab_file_rollback():
    instance = {'auth_type': 'kerberos', 'kerberos_auth': 'disabled', 'kerberos_keytab': '/test/file'}
    transport = EnvironmentRecordingTransport('KRB5_CLIENT_KTNAME')
    transport.respond()
    http = _create_requests_client(instance, transport)

    with EnvVars({'KRB5_CLIENT_KTNAME': 'old'}):
        assert os.environ.get('KRB5_CLIENT_KTNAME') == 'old'

        response = http.get('http://www.google.com')

        assert response.status_code == 200
        assert transport.values == ['/test/file']
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
