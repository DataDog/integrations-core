# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
from collections import OrderedDict

import mock
import pytest
import requests
import requests_kerberos
import requests_ntlm
from aws_requests_auth import boto_utils as requests_aws
from requests import auth as requests_auth
from requests.exceptions import ConnectTimeout, ProxyError
from six import iteritems
from urllib3.exceptions import InsecureRequestWarning

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.http import STANDARD_FIELDS, RequestsWrapper
from datadog_checks.dev import EnvVars
from datadog_checks.dev.utils import running_on_windows_ci

pytestmark = pytest.mark.http

DEFAULT_OPTIONS = {
    'auth': None,
    'cert': None,
    'headers': OrderedDict([('User-Agent', 'Datadog Agent/0.0.0')]),
    'proxies': None,
    'timeout': (10.0, 10.0),
    'verify': True,
}


class TestAttribute:
    def test_default(self):
        check = AgentCheck('test', {}, [{}])

        assert check._http is None

    def test_activate(self):
        check = AgentCheck('test', {}, [{}])

        assert check.http == check._http
        assert isinstance(check.http, RequestsWrapper)


class TestTimeout:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        # Assert the timeout is slightly larger than a multiple of 3,
        # which is the default TCP packet retransmission window. See:
        # https://tools.ietf.org/html/rfc2988
        assert 0 < http.options['timeout'][0] % 3 <= 1

    def test_config_timeout(self):
        instance = {'timeout': 24.5}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['timeout'] == (24.5, 24.5)

    def test_config_multiple_timeouts(self):
        instance = {'read_timeout': 4, 'connect_timeout': 10}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['timeout'] == (10, 4)

    def test_config_init_config_override(self):
        instance = {}
        init_config = {'timeout': 16}
        http = RequestsWrapper(instance, init_config)

        assert http.options['timeout'] == (16, 16)


class TestHeaders:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['headers'] == {'User-Agent': 'Datadog Agent/0.0.0'}

    def test_config_headers(self):
        headers = OrderedDict((('key1', 'value1'), ('key2', 'value2')))
        instance = {'headers': headers}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert list(iteritems(http.options['headers'])) == list(iteritems(headers))

    def test_config_headers_string_values(self):
        instance = {'headers': {'answer': 42}}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['headers'] == {'answer': '42'}

    def test_config_extra_headers(self):
        headers = OrderedDict((('key1', 'value1'), ('key2', 'value2')))
        instance = {'extra_headers': headers}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        complete_headers = OrderedDict({'User-Agent': 'Datadog Agent/0.0.0'})
        complete_headers.update(headers)
        assert list(iteritems(http.options['headers'])) == list(iteritems(complete_headers))

    def test_config_extra_headers_string_values(self):
        instance = {'extra_headers': {'answer': 42}}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['headers'] == {'User-Agent': 'Datadog Agent/0.0.0', 'answer': '42'}

    def test_extra_headers_on_http_method_call(self):
        instance = {'extra_headers': {'answer': 42}}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        extra_headers = {"foo": "bar"}
        with mock.patch("requests.get") as get:
            http.get("http://example.com/hello", extra_headers=extra_headers)

            expected_options = {'foo': 'bar', 'User-Agent': 'Datadog Agent/0.0.0', 'answer': '42'}
            get.assert_called_with(
                "http://example.com/hello",
                headers=expected_options,
                auth=None,
                cert=None,
                proxies=None,
                timeout=(10.0, 10.0),
                verify=True,
            )

        # make sure the original headers are not modified
        assert http.options['headers'] == {'User-Agent': 'Datadog Agent/0.0.0', 'answer': '42'}
        assert extra_headers == {"foo": "bar"}


class TestVerify:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['verify'] is True

    def test_config_verify(self):
        instance = {'tls_verify': False}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['verify'] is False

    def test_config_ca_cert(self):
        instance = {'tls_ca_cert': 'ca_cert'}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['verify'] == 'ca_cert'

    def test_config_verify_and_ca_cert(self):
        instance = {'tls_verify': True, 'tls_ca_cert': 'ca_cert'}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['verify'] == 'ca_cert'


class TestCert:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['cert'] is None

    def test_config_cert(self):
        instance = {'tls_cert': 'cert'}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['cert'] == 'cert'

    def test_config_cert_and_private_key(self):
        instance = {'tls_cert': 'cert', 'tls_private_key': 'key'}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['cert'] == ('cert', 'key')


class TestAuth:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['auth'] is None

    def test_config_basic(self):
        instance = {'username': 'user', 'password': 'pass'}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['auth'] == ('user', 'pass')

    def test_config_basic_authtype(self):
        instance = {'username': 'user', 'password': 'pass', 'auth_type': 'basic'}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['auth'] == ('user', 'pass')

    def test_config_digest_authtype(self):
        instance = {'username': 'user', 'password': 'pass', 'auth_type': 'digest'}
        init_config = {}
        http = RequestsWrapper(instance, init_config)
        assert isinstance(http.options['auth'], requests_auth.HTTPDigestAuth)

        with mock.patch('datadog_checks.base.utils.http.requests_auth.HTTPDigestAuth') as m:
            RequestsWrapper(instance, init_config)

            m.assert_called_once_with('user', 'pass')

    def test_config_basic_only_username(self):
        instance = {'username': 'user'}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['auth'] is None

    def test_config_basic_only_password(self):
        instance = {'password': 'pass'}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['auth'] is None

    def test_config_kerberos_legacy(self):
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

    def test_config_kerberos(self):
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

    def test_config_kerberos_shortcut(self):
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

    def test_config_kerberos_unknown(self):
        instance = {'auth_type': 'kerberos', 'kerberos_auth': 'unknown'}
        init_config = {}

        with pytest.raises(ConfigurationError):
            RequestsWrapper(instance, init_config)

    def test_config_kerberos_keytab_file(self):
        instance = {'auth_type': 'kerberos', 'kerberos_keytab': '/test/file'}
        init_config = {}

        http = RequestsWrapper(instance, init_config)

        assert os.environ.get('KRB5_CLIENT_KTNAME') is None

        with mock.patch('requests.get', side_effect=lambda *args, **kwargs: os.environ.get('KRB5_CLIENT_KTNAME')):
            assert http.get('https://www.google.com') == '/test/file'

        assert os.environ.get('KRB5_CLIENT_KTNAME') is None

    def test_config_kerberos_cache(self):
        instance = {'auth_type': 'kerberos', 'kerberos_cache': '/test/file'}
        init_config = {}

        http = RequestsWrapper(instance, init_config)

        assert os.environ.get('KRB5CCNAME') is None

        with mock.patch('requests.get', side_effect=lambda *args, **kwargs: os.environ.get('KRB5CCNAME')):
            assert http.get('https://www.google.com') == '/test/file'

        assert os.environ.get('KRB5CCNAME') is None

    def test_config_kerberos_cache_restores_rollback(self):
        instance = {'auth_type': 'kerberos', 'kerberos_cache': '/test/file'}
        init_config = {}

        http = RequestsWrapper(instance, init_config)

        with EnvVars({'KRB5CCNAME': 'old'}):
            with mock.patch('requests.get', side_effect=lambda *args, **kwargs: os.environ.get('KRB5CCNAME')):
                assert http.get('https://www.google.com') == '/test/file'

            assert os.environ.get('KRB5CCNAME') == 'old'

    def test_config_kerberos_keytab_file_rollback(self):
        instance = {'auth_type': 'kerberos', 'kerberos_keytab': '/test/file'}
        init_config = {}

        http = RequestsWrapper(instance, init_config)

        with EnvVars({'KRB5_CLIENT_KTNAME': 'old'}):
            assert os.environ.get('KRB5_CLIENT_KTNAME') == 'old'

            with mock.patch('requests.get', side_effect=lambda *args, **kwargs: os.environ.get('KRB5_CLIENT_KTNAME')):
                assert http.get('https://www.google.com') == '/test/file'

            assert os.environ.get('KRB5_CLIENT_KTNAME') == 'old'

    def test_config_kerberos_legacy_remap(self):
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

    @pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
    def test_kerberos_auth_noconf(self, kerberos):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)
        response = http.get(kerberos["url"])

        assert response.status_code == 401

    @pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
    def test_kerberos_auth_principal_inexistent(self, kerberos):
        instance = {
            'url': kerberos["url"],
            'auth_type': 'kerberos',
            'kerberos_auth': 'required',
            'kerberos_hostname': kerberos["hostname"],
            'kerberos_cache': "DIR:{}".format(kerberos["cache"]),
            'kerberos_keytab': kerberos["keytab"],
            'kerberos_principal': "user/doesnotexist@{}".format(kerberos["realm"]),
            'kerberos_force_initiate': 'false',
        }
        init_config = {}
        http = RequestsWrapper(instance, init_config)
        response = http.get(instance["url"])
        assert response.status_code == 401

    @pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
    def test_kerberos_auth_principal_incache_nokeytab(self, kerberos):
        instance = {
            'url': kerberos["url"],
            'auth_type': 'kerberos',
            'kerberos_auth': 'required',
            'kerberos_cache': "DIR:{}".format(kerberos["cache"]),
            'kerberos_hostname': kerberos["hostname"],
            'kerberos_principal': "user/nokeytab@{}".format(kerberos["realm"]),
            'kerberos_force_initiate': 'true',
        }
        init_config = {}
        http = RequestsWrapper(instance, init_config)
        response = http.get(instance["url"])
        assert response.status_code == 200

    @pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
    def test_kerberos_auth_principal_inkeytab_nocache(self, kerberos):
        instance = {
            'url': kerberos["url"],
            'auth_type': 'kerberos',
            'kerberos_auth': 'required',
            'kerberos_hostname': kerberos["hostname"],
            'kerberos_cache': "DIR:{}".format(kerberos["tmp_dir"]),
            'kerberos_keytab': kerberos["keytab"],
            'kerberos_principal': "user/inkeytab@{}".format(kerberos["realm"]),
            'kerberos_force_initiate': 'true',
        }
        init_config = {}
        http = RequestsWrapper(instance, init_config)
        response = http.get(instance["url"])
        assert response.status_code == 200

    def test_config_ntlm(self):
        instance = {'auth_type': 'ntlm', 'ntlm_domain': 'domain\\user', 'password': 'pass'}
        init_config = {}

        # Trigger lazy import
        http = RequestsWrapper(instance, init_config)
        assert isinstance(http.options['auth'], requests_ntlm.HttpNtlmAuth)

        with mock.patch('datadog_checks.base.utils.http.requests_ntlm.HttpNtlmAuth') as m:
            RequestsWrapper(instance, init_config)

            m.assert_called_once_with('domain\\user', 'pass')

    def test_config_ntlm_legacy(self, caplog):
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

    def test_config_aws(self):
        instance = {'auth_type': 'aws', 'aws_host': 'uri', 'aws_region': 'earth', 'aws_service': 'saas'}
        init_config = {}

        # Trigger lazy import
        http = RequestsWrapper(instance, init_config)
        assert isinstance(http.options['auth'], requests_aws.BotoAWSRequestsAuth)

        with mock.patch('datadog_checks.base.utils.http.requests_aws.BotoAWSRequestsAuth') as m:
            RequestsWrapper(instance, init_config)

            m.assert_called_once_with(aws_host='uri', aws_region='earth', aws_service='saas')

    def test_config_aws_service_remapper(self):
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
    def test_config_aws_invalid_cases(self, case, instance, match):
        init_config = {}
        with pytest.raises(ConfigurationError, match=match):
            RequestsWrapper(instance, init_config)


class TestProxies:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['proxies'] is None
        assert http.no_proxy_uris is None

    def test_config_proxy_agent(self):
        with mock.patch(
            'datadog_checks.base.stubs.datadog_agent.get_config',
            return_value={'http': 'http_host', 'https': 'https_host', 'no_proxy': 'uri1,uri2;uri3,uri4'},
        ):
            instance = {}
            init_config = {}
            http = RequestsWrapper(instance, init_config)

            assert http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
            assert http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']

    def test_config_proxy_init_config_override(self):
        with mock.patch(
            'datadog_checks.base.stubs.datadog_agent.get_config',
            return_value={'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'},
        ):
            instance = {}
            init_config = {'proxy': {'http': 'http_host', 'https': 'https_host', 'no_proxy': 'uri1,uri2;uri3,uri4'}}
            http = RequestsWrapper(instance, init_config)

            assert http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
            assert http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']

    def test_config_proxy_instance_override(self):
        with mock.patch(
            'datadog_checks.base.stubs.datadog_agent.get_config',
            return_value={'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'},
        ):
            instance = {'proxy': {'http': 'http_host', 'https': 'https_host', 'no_proxy': 'uri1,uri2;uri3,uri4'}}
            init_config = {'proxy': {'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'}}
            http = RequestsWrapper(instance, init_config)

            assert http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
            assert http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']

    def test_config_no_proxy_as_list(self):
        with mock.patch(
            'datadog_checks.base.stubs.datadog_agent.get_config',
            return_value={'http': 'http_host', 'https': 'https_host', 'no_proxy': ['uri1', 'uri2', 'uri3', 'uri4']},
        ):
            instance = {}
            init_config = {}
            http = RequestsWrapper(instance, init_config)

            assert http.options['proxies'] == {'http': 'http_host', 'https': 'https_host'}
            assert http.no_proxy_uris == ['uri1', 'uri2', 'uri3', 'uri4']

    def test_config_proxy_skip(self):
        instance = {'proxy': {'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'}, 'skip_proxy': True}
        init_config = {'proxy': {'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'}}
        http = RequestsWrapper(instance, init_config)

        assert http.options['proxies'] == {'http': '', 'https': ''}
        assert http.no_proxy_uris is None

    def test_config_proxy_skip_init_config(self):
        instance = {'proxy': {'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'}}
        init_config = {'proxy': {'http': 'unused', 'https': 'unused', 'no_proxy': 'unused'}, 'skip_proxy': True}
        http = RequestsWrapper(instance, init_config)

        assert http.options['proxies'] == {'http': '', 'https': ''}
        assert http.no_proxy_uris is None

    def test_proxy_env_vars_skip(self):
        instance = {'skip_proxy': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with EnvVars({'HTTP_PROXY': 'http://1.2.3.4:567'}):
            response = http.get('http://www.google.com')
            response.raise_for_status()

        with EnvVars({'HTTPS_PROXY': 'https://1.2.3.4:567'}):
            response = http.get('https://www.google.com')
            response.raise_for_status()

    def test_proxy_env_vars_override_skip_fail(self):
        instance = {'skip_proxy': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with EnvVars({'HTTP_PROXY': 'http://1.2.3.4:567'}):
            with pytest.raises((ConnectTimeout, ProxyError)):
                http.get('http://www.google.com', timeout=1, proxies=None)

        with EnvVars({'HTTPS_PROXY': 'https://1.2.3.4:567'}):
            with pytest.raises((ConnectTimeout, ProxyError)):
                http.get('https://www.google.com', timeout=1, proxies=None)

    def test_proxy_bad(self):
        instance = {'proxy': {'http': 'http://1.2.3.4:567', 'https': 'https://1.2.3.4:567'}}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with pytest.raises((ConnectTimeout, ProxyError)):
            http.get('http://www.google.com', timeout=1)

        with pytest.raises((ConnectTimeout, ProxyError)):
            http.get('https://www.google.com', timeout=1)

    def test_proxy_bad_no_proxy_override_success(self):
        instance = {
            'proxy': {'http': 'http://1.2.3.4:567', 'https': 'https://1.2.3.4:567', 'no_proxy': 'unused,google.com'}
        }
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        response = http.get('http://www.google.com')
        response.raise_for_status()

        response = http.get('https://www.google.com')
        response.raise_for_status()

    def test_no_proxy_uris_coverage(self):
        http = RequestsWrapper({}, {})

        # Coverage is not smart enough to detect that looping an empty
        # iterable will never occur when gated by `if iterable:`.
        http.no_proxy_uris = mock.MagicMock()

        http.no_proxy_uris.__iter__ = lambda self, *args, **kwargs: iter([])
        http.no_proxy_uris.__bool__ = lambda self, *args, **kwargs: True
        # TODO: Remove with Python 2
        http.no_proxy_uris.__nonzero__ = lambda self, *args, **kwargs: True

        http.get('https://www.google.com')

    @pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
    def test_socks5_proxy(self, socks5_proxy):
        instance = {'proxy': {'http': 'socks5h://{}'.format(socks5_proxy)}}
        init_config = {}
        http = RequestsWrapper(instance, init_config)
        http.get('http://www.google.com')
        http.get('http://nginx')

    @pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
    def test_no_proxy_domain(self, socks5_proxy):
        instance = {'proxy': {'http': 'http://1.2.3.4:567', 'no_proxy': '.google.com,example.com,9'}}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        # no_proxy match: .google.com
        http.get('http://www.google.com')

        # no_proxy match: example.com
        http.get('http://www.example.com')
        http.get('http://example.com')

        # no_proxy match: 9
        http.get('http://127.0.0.9')

    @pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
    def test_no_proxy_domain_fail(self, socks5_proxy):
        instance = {'proxy': {'http': 'http://1.2.3.4:567', 'no_proxy': '.google.com,example.com,example,9'}}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        # no_proxy not match: .google.com
        # ".y.com" matches "x.y.com" but not "y.com"
        with pytest.raises((ConnectTimeout, ProxyError)):
            http.get('http://google.com', timeout=1)

        # no_proxy not match: example or example.com
        with pytest.raises((ConnectTimeout, ProxyError)):
            http.get('http://notexample.com', timeout=1)

        with pytest.raises((ConnectTimeout, ProxyError)):
            http.get('http://example.org', timeout=1)

        # no_proxy not match: 9
        with pytest.raises((ConnectTimeout, ProxyError)):
            http.get('http://127.0.0.99', timeout=1)

    @pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
    def test_no_proxy_ip(self, socks5_proxy):
        instance = {
            'proxy': {
                'http': 'http://1.2.3.4:567',
                'no_proxy': '127.0.0.1,127.0.0.2/32,127.1.0.0/25,127.1.1.0/255.255.255.128,127.1.2.0/0.0.0.127',
            }
        }
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        # no_proxy match: 127.0.0.1
        http.get('http://127.0.0.1', timeout=1)

        # no_proxy match: 127.0.0.2/32
        http.get('http://127.0.0.2', timeout=1)

        # no_proxy match: IP within 127.1.0.0/25 subnet - cidr bits format
        http.get('http://127.1.0.50', timeout=1)
        http.get('http://127.1.0.100', timeout=1)

        # no_proxy match: IP within 127.1.1.0/255.255.255.128 subnet - net mask format
        http.get('http://127.1.1.50', timeout=1)
        http.get('http://127.1.1.100', timeout=1)

        # no_proxy match: IP within 127.1.2.0/0.0.0.127 subnet - host mask format
        http.get('http://127.1.2.50', timeout=1)
        http.get('http://127.1.2.100', timeout=1)

    @pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
    def test_no_proxy_ip_fail(self, socks5_proxy):
        instance = {
            'proxy': {
                'http': 'http://1.2.3.4:567',
                'no_proxy': '127.0.0.1,127.0.0.2/32,127.1.0.0/25,127.1.1.0/255.255.255.128,127.1.2.0/0.0.0.127',
            }
        }
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        # no_proxy not match: 127.0.0.1
        with pytest.raises((ConnectTimeout, ProxyError)):
            http.get('http://127.0.0.11', timeout=1)

        # no_proxy not match: 127.0.0.2/32
        with pytest.raises((ConnectTimeout, ProxyError)):
            http.get('http://127.0.0.22', timeout=1)

        # no_proxy not match: IP outside 127.1.0.0/25 subnet - cidr bits format
        with pytest.raises((ConnectTimeout, ProxyError)):
            http.get('http://127.1.0.150', timeout=1)
            http.get('http://127.1.0.200', timeout=1)

        # no_proxy not match: IP outside 127.1.1.0/255.255.255.128 subnet - net mask format
        with pytest.raises((ConnectTimeout, ProxyError)):
            http.get('http://127.1.1.150', timeout=1)
            http.get('http://127.1.1.200', timeout=1)

        # no_proxy not match: IP outside 127.1.2.0/0.0.0.127 subnet - host mask format
        with pytest.raises((ConnectTimeout, ProxyError)):
            http.get('http://127.1.2.150', timeout=1)
            http.get('http://127.1.2.200', timeout=1)


class TestIgnoreTLSWarning:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.ignore_tls_warning is False

    def test_config_flag(self):
        instance = {'tls_ignore_warning': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.ignore_tls_warning is True

    def test_init_config_flag(self):
        instance = {}
        init_config = {'tls_ignore_warning': True}

        http = RequestsWrapper(instance, init_config)

        assert http.ignore_tls_warning is True

    def test_instance_and_init_flag(self):
        instance = {'tls_ignore_warning': False}
        init_config = {'tls_ignore_warning': True}

        http = RequestsWrapper(instance, init_config)

        assert http.ignore_tls_warning is False

    def test_default_no_ignore(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with pytest.warns(InsecureRequestWarning):
            http.get('https://www.google.com', verify=False)

    def test_ignore(self):
        instance = {'tls_ignore_warning': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with pytest.warns(None) as record:
            http.get('https://www.google.com', verify=False)

        assert all(not issubclass(warning.category, InsecureRequestWarning) for warning in record)

    def test_default_no_ignore_session(self):
        instance = {'persist_connections': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with pytest.warns(InsecureRequestWarning):
            http.get('https://www.google.com', verify=False)

    def test_ignore_session(self):
        instance = {'tls_ignore_warning': True, 'persist_connections': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with pytest.warns(None) as record:
            http.get('https://www.google.com', verify=False)

        assert all(not issubclass(warning.category, InsecureRequestWarning) for warning in record)

    def test_init_ignore(self):
        instance = {}
        init_config = {'tls_ignore_warning': True}
        http = RequestsWrapper(instance, init_config)

        with pytest.warns(None) as record:
            http.get('https://www.google.com', verify=False)

        assert all(not issubclass(warning.category, InsecureRequestWarning) for warning in record)

    def test_default_init_no_ignore(self):
        instance = {}
        init_config = {'tls_ignore_warning': False}
        http = RequestsWrapper(instance, init_config)

        with pytest.warns(InsecureRequestWarning):
            http.get('https://www.google.com', verify=False)

    def test_instance_ignore(self):
        instance = {'tls_ignore_warning': True}
        init_config = {'tls_ignore_warning': False}
        http = RequestsWrapper(instance, init_config)

        with pytest.warns(None) as record:
            http.get('https://www.google.com', verify=False)

        assert all(not issubclass(warning.category, InsecureRequestWarning) for warning in record)

    def test_instance_no_ignore(self):
        instance = {'tls_ignore_warning': False}
        init_config = {'tls_ignore_warning': True}
        http = RequestsWrapper(instance, init_config)

        with pytest.warns(InsecureRequestWarning):
            http.get('https://www.google.com', verify=False)


class TestSession:
    def test_default_none(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http._session is None

    def test_lazy_create(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.session is http._session
        assert isinstance(http.session, requests.Session)

    def test_attributes(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        for key, value in iteritems(http.options):
            assert hasattr(http.session, key)
            assert getattr(http.session, key) == value


class TestRemapper:
    def test_legacy_no_proxy(self):
        instance = {'no_proxy': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['proxies'] == {'http': '', 'https': ''}
        assert http.no_proxy_uris is None

    def test_no_default(self):
        instance = {}
        init_config = {}
        remapper = {'prometheus_timeout': {'name': 'timeout'}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.options['timeout'] == (STANDARD_FIELDS['timeout'], STANDARD_FIELDS['timeout'])

    def test_invert(self):
        instance = {'disable_ssl_validation': False}
        init_config = {}
        remapper = {'disable_ssl_validation': {'name': 'tls_verify', 'default': False, 'invert': True}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.options['verify'] is True

    def test_invert_without_explicit_default(self):
        instance = {}
        init_config = {}
        remapper = {'disable_ssl_validation': {'name': 'tls_verify', 'invert': True}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.options['verify'] is True

    def test_standard_override(self):
        instance = {'disable_ssl_validation': True, 'tls_verify': False}
        init_config = {}
        remapper = {'disable_ssl_validation': {'name': 'tls_verify', 'default': False, 'invert': True}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.options['verify'] is False

    def test_unknown_name_default(self):
        instance = {}
        init_config = {}
        remapper = {'verify_tls': {'name': 'verify', 'default': False}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.options['verify'] is True


class TestLogger:
    def test_default(self, caplog):
        check = AgentCheck('test', {}, [{}])

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            check.http.get('https://www.google.com')

        expected_message = 'Sending GET request to https://www.google.com'
        for _, _, message in caplog.record_tuples:
            assert message != expected_message

    def test_instance(self, caplog):
        instance = {'log_requests': True}
        init_config = {}
        check = AgentCheck('test', init_config, [instance])

        assert check.http.logger is check.log

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            check.http.get('https://www.google.com')

        expected_message = 'Sending GET request to https://www.google.com'
        for _, level, message in caplog.record_tuples:
            if level == logging.DEBUG and message == expected_message:
                break
        else:
            raise AssertionError('Expected DEBUG log with message `{}`'.format(expected_message))

    def test_init_config(self, caplog):
        instance = {}
        init_config = {'log_requests': True}
        check = AgentCheck('test', init_config, [instance])

        assert check.http.logger is check.log

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            check.http.get('https://www.google.com')

        expected_message = 'Sending GET request to https://www.google.com'
        for _, level, message in caplog.record_tuples:
            if level == logging.DEBUG and message == expected_message:
                break
        else:
            raise AssertionError('Expected DEBUG log with message `{}`'.format(expected_message))

    def test_instance_override(self, caplog):
        instance = {'log_requests': False}
        init_config = {'log_requests': True}
        check = AgentCheck('test', init_config, [instance])

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            check.http.get('https://www.google.com')

        expected_message = 'Sending GET request to https://www.google.com'
        for _, _, message in caplog.record_tuples:
            assert message != expected_message


class TestAPI:
    def test_get(self):
        http = RequestsWrapper({}, {})

        with mock.patch('requests.get'):
            http.get('https://www.google.com')
            requests.get.assert_called_once_with('https://www.google.com', **http.options)

    def test_get_session(self):
        http = RequestsWrapper({'persist_connections': True}, {})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.get('https://www.google.com')
            http.session.get.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)

    def test_get_option_override(self):
        http = RequestsWrapper({}, {})
        options = http.options.copy()
        options['auth'] = ('user', 'pass')

        with mock.patch('requests.get'):
            http.get('https://www.google.com', auth=options['auth'])
            requests.get.assert_called_once_with('https://www.google.com', **options)

    def test_get_session_option_override(self):
        http = RequestsWrapper({}, {})
        options = DEFAULT_OPTIONS.copy()
        options.update({'auth': ('user', 'pass')})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.get('https://www.google.com', persist=True, auth=options['auth'])
            http.session.get.assert_called_once_with('https://www.google.com', **options)

    def test_post(self):
        http = RequestsWrapper({}, {})

        with mock.patch('requests.post'):
            http.post('https://www.google.com')
            requests.post.assert_called_once_with('https://www.google.com', **http.options)

    def test_post_session(self):
        http = RequestsWrapper({'persist_connections': True}, {})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.post('https://www.google.com')
            http.session.post.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)

    def test_post_option_override(self):
        http = RequestsWrapper({}, {})
        options = http.options.copy()
        options['auth'] = ('user', 'pass')

        with mock.patch('requests.post'):
            http.post('https://www.google.com', auth=options['auth'])
            requests.post.assert_called_once_with('https://www.google.com', **options)

    def test_post_session_option_override(self):
        http = RequestsWrapper({}, {})
        options = DEFAULT_OPTIONS.copy()
        options.update({'auth': ('user', 'pass')})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.post('https://www.google.com', persist=True, auth=options['auth'])
            http.session.post.assert_called_once_with('https://www.google.com', **options)

    def test_head(self):
        http = RequestsWrapper({}, {})

        with mock.patch('requests.head'):
            http.head('https://www.google.com')
            requests.head.assert_called_once_with('https://www.google.com', **http.options)

    def test_head_session(self):
        http = RequestsWrapper({'persist_connections': True}, {})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.head('https://www.google.com')
            http.session.head.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)

    def test_head_option_override(self):
        http = RequestsWrapper({}, {})
        options = http.options.copy()
        options['auth'] = ('user', 'pass')

        with mock.patch('requests.head'):
            http.head('https://www.google.com', auth=options['auth'])
            requests.head.assert_called_once_with('https://www.google.com', **options)

    def test_head_session_option_override(self):
        http = RequestsWrapper({}, {})
        options = DEFAULT_OPTIONS.copy()
        options.update({'auth': ('user', 'pass')})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.head('https://www.google.com', persist=True, auth=options['auth'])
            http.session.head.assert_called_once_with('https://www.google.com', **options)

    def test_put(self):
        http = RequestsWrapper({}, {})

        with mock.patch('requests.put'):
            http.put('https://www.google.com')
            requests.put.assert_called_once_with('https://www.google.com', **http.options)

    def test_put_session(self):
        http = RequestsWrapper({'persist_connections': True}, {})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.put('https://www.google.com')
            http.session.put.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)

    def test_put_option_override(self):
        http = RequestsWrapper({}, {})
        options = http.options.copy()
        options['auth'] = ('user', 'pass')

        with mock.patch('requests.put'):
            http.put('https://www.google.com', auth=options['auth'])
            requests.put.assert_called_once_with('https://www.google.com', **options)

    def test_put_session_option_override(self):
        http = RequestsWrapper({}, {})
        options = DEFAULT_OPTIONS.copy()
        options.update({'auth': ('user', 'pass')})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.put('https://www.google.com', persist=True, auth=options['auth'])
            http.session.put.assert_called_once_with('https://www.google.com', **options)

    def test_patch(self):
        http = RequestsWrapper({}, {})

        with mock.patch('requests.patch'):
            http.patch('https://www.google.com')
            requests.patch.assert_called_once_with('https://www.google.com', **http.options)

    def test_patch_session(self):
        http = RequestsWrapper({'persist_connections': True}, {})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.patch('https://www.google.com')
            http.session.patch.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)

    def test_patch_option_override(self):
        http = RequestsWrapper({}, {})
        options = http.options.copy()
        options['auth'] = ('user', 'pass')

        with mock.patch('requests.patch'):
            http.patch('https://www.google.com', auth=options['auth'])
            requests.patch.assert_called_once_with('https://www.google.com', **options)

    def test_patch_session_option_override(self):
        http = RequestsWrapper({}, {})
        options = DEFAULT_OPTIONS.copy()
        options.update({'auth': ('user', 'pass')})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.patch('https://www.google.com', persist=True, auth=options['auth'])
            http.session.patch.assert_called_once_with('https://www.google.com', **options)

    def test_delete(self):
        http = RequestsWrapper({}, {})

        with mock.patch('requests.delete'):
            http.delete('https://www.google.com')
            requests.delete.assert_called_once_with('https://www.google.com', **http.options)

    def test_delete_session(self):
        http = RequestsWrapper({'persist_connections': True}, {})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.delete('https://www.google.com')
            http.session.delete.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)

    def test_delete_option_override(self):
        http = RequestsWrapper({}, {})
        options = http.options.copy()
        options['auth'] = ('user', 'pass')

        with mock.patch('requests.delete'):
            http.delete('https://www.google.com', auth=options['auth'])
            requests.delete.assert_called_once_with('https://www.google.com', **options)

    def test_delete_session_option_override(self):
        http = RequestsWrapper({}, {})
        options = DEFAULT_OPTIONS.copy()
        options.update({'auth': ('user', 'pass')})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.delete('https://www.google.com', persist=True, auth=options['auth'])
            http.session.delete.assert_called_once_with('https://www.google.com', **options)


class TestIntegration:
    def test_session_timeout(self):
        http = RequestsWrapper({'persist_connections': True}, {'timeout': 0.08})
        with pytest.raises(requests.exceptions.Timeout):
            http.get('https://httpbin.org/delay/0.10')
