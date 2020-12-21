# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
import re
from collections import OrderedDict

import jwt
import mock
import pytest
import requests
import requests_kerberos
import requests_ntlm
import requests_unixsocket
from aws_requests_auth import boto_utils as requests_aws
from requests import auth as requests_auth
from requests.exceptions import ConnectTimeout, ProxyError
from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.headers import headers as agent_headers
from datadog_checks.base.utils.http import STANDARD_FIELDS, RequestsWrapper, is_uds_url, quote_uds_url
from datadog_checks.base.utils.time import get_timestamp
from datadog_checks.dev import EnvVars, TempDir
from datadog_checks.dev.utils import ON_WINDOWS, read_file, running_on_windows_ci, write_file

pytestmark = pytest.mark.http

DEFAULT_OPTIONS = {
    'auth': None,
    'cert': None,
    'headers': OrderedDict(
        [
            ('User-Agent', 'Datadog Agent/0.0.0'),
            ('Accept', '*/*'),
            ('Accept-Encoding', 'gzip, deflate'),
        ]
    ),
    'proxies': None,
    'timeout': (10.0, 10.0),
    'verify': True,
}


class TestAttribute:
    def test_default(self):
        check = AgentCheck('test', {}, [{}])

        assert not hasattr(check, '_http')

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
    def test_agent_headers(self):
        # This helper is not used by the RequestsWrapper, but some integrations may use it.
        # So we provide a unit test for it.
        agent_config = {}
        headers = agent_headers(agent_config)
        assert headers == DEFAULT_OPTIONS['headers']

    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['headers'] == DEFAULT_OPTIONS['headers']

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

        complete_headers = OrderedDict(DEFAULT_OPTIONS['headers'])
        complete_headers.update(headers)
        assert list(iteritems(http.options['headers'])) == list(iteritems(complete_headers))

    def test_config_extra_headers_string_values(self):
        instance = {'extra_headers': {'answer': 42}}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        complete_headers = dict(DEFAULT_OPTIONS['headers'])
        complete_headers.update({'answer': '42'})
        assert http.options['headers'] == complete_headers

    def test_extra_headers_on_http_method_call(self):
        instance = {'extra_headers': {'answer': 42}}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        complete_headers = dict(DEFAULT_OPTIONS['headers'])
        complete_headers.update({'answer': '42'})

        extra_headers = {"foo": "bar"}
        with mock.patch("requests.get") as get:
            http.get("http://example.com/hello", extra_headers=extra_headers)

            expected_options = dict(complete_headers)
            expected_options.update(extra_headers)

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
        assert http.options['headers'] == complete_headers
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

    def test_config_basic_no_legacy_encoding(self):
        instance = {'username': 'user', 'password': 'pass', 'use_legacy_auth_encoding': False}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['auth'] == (b'user', b'pass')

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

    @pytest.mark.skipif(True, reason='Test fixture for Agent QA only')
    def test_kerberos_auth_with_agent(self, kerberos_agent):
        """
        Test setup to verify kerberos authorization from an actual Agent container.

        Steps to reproduce:
        1. Change decorator above from `True` to `False` to enable test
        2. Edit compose/kerberos-agent/Dockerfile to appropriate Agent release
        3. Run test via `ddev test -k test_kerberos_auth_with_agent datadog_checks_base:py38`
        4. After compose builds, exec into Agent container via `docker exec -it compose_agent_1 /bin/bash`
        5. Execute check via `agent check nginx` and verify successful result.
        6. Exit test via Ctrl-C (test will show as failed, but that's okay)
        """

        instance = {
            'url': kerberos_agent["url"],
            'auth_type': 'kerberos',
            'kerberos_auth': 'required',
            'kerberos_hostname': kerberos_agent["hostname"],
            'kerberos_cache': "DIR:{}".format(kerberos_agent["tmp_dir"]),
            'kerberos_keytab': kerberos_agent["keytab"],
            'kerberos_principal': "user/inkeytab@{}".format(kerberos_agent["realm"]),
            'kerberos_force_initiate': 'true',
        }
        init_config = {}
        http = RequestsWrapper(instance, init_config)
        response = http.get(instance["url"])

        import time
        time.sleep(3600)

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


class TestAuthTokenHandlerCreation:
    def test_not_mapping(self):
        instance = {'auth_token': ''}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The `auth_token` field must be a mapping$'):
            RequestsWrapper(instance, init_config)

    def test_no_reader(self):
        instance = {'auth_token': {'writer': {}}}
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `auth_token` field must define both `reader` and `writer` settings$'
        ):
            RequestsWrapper(instance, init_config)

    def test_no_writer(self):
        instance = {'auth_token': {'reader': {}}}
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `auth_token` field must define both `reader` and `writer` settings$'
        ):
            RequestsWrapper(instance, init_config)

    def test_reader_config_not_mapping(self):
        instance = {'auth_token': {'reader': '', 'writer': {}}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The `reader` settings of field `auth_token` must be a mapping$'):
            RequestsWrapper(instance, init_config)

    def test_writer_config_not_mapping(self):
        instance = {'auth_token': {'reader': {}, 'writer': ''}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The `writer` settings of field `auth_token` must be a mapping$'):
            RequestsWrapper(instance, init_config)

    def test_reader_type_missing(self):
        instance = {'auth_token': {'reader': {}, 'writer': {}}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The reader `type` of field `auth_token` is required$'):
            RequestsWrapper(instance, init_config)

    def test_reader_type_not_string(self):
        instance = {'auth_token': {'reader': {'type': {}}, 'writer': {}}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The reader `type` of field `auth_token` must be a string$'):
            RequestsWrapper(instance, init_config)

    def test_reader_type_unknown(self):
        instance = {'auth_token': {'reader': {'type': 'foo'}, 'writer': {}}}
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^Unknown `auth_token` reader type, must be one of: dcos_auth, file$'
        ):
            RequestsWrapper(instance, init_config)

    def test_writer_type_missing(self):
        instance = {'auth_token': {'reader': {'type': 'file'}, 'writer': {}}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The writer `type` of field `auth_token` is required$'):
            RequestsWrapper(instance, init_config)

    def test_writer_type_not_string(self):
        instance = {'auth_token': {'reader': {'type': 'file'}, 'writer': {'type': {}}}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The writer `type` of field `auth_token` must be a string$'):
            RequestsWrapper(instance, init_config)

    def test_writer_type_unknown(self):
        instance = {'auth_token': {'reader': {'type': 'file'}, 'writer': {'type': 'foo'}}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^Unknown `auth_token` writer type, must be one of: header$'):
            RequestsWrapper(instance, init_config)


class TestAuthTokenFileReaderCreation:
    def test_path_missing(self):
        instance = {'auth_token': {'reader': {'type': 'file'}, 'writer': {'type': 'header'}}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The `path` setting of `auth_token` reader is required$'):
            RequestsWrapper(instance, init_config)

    def test_path_not_string(self):
        instance = {'auth_token': {'reader': {'type': 'file', 'path': {}}, 'writer': {'type': 'header'}}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The `path` setting of `auth_token` reader must be a string$'):
            RequestsWrapper(instance, init_config)

    def test_pattern_not_string(self):
        instance = {
            'auth_token': {'reader': {'type': 'file', 'path': '/foo', 'pattern': 0}, 'writer': {'type': 'header'}}
        }
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The `pattern` setting of `auth_token` reader must be a string$'):
            RequestsWrapper(instance, init_config)

    def test_pattern_no_groups(self):
        instance = {
            'auth_token': {'reader': {'type': 'file', 'path': '/foo', 'pattern': 'bar'}, 'writer': {'type': 'header'}}
        }
        init_config = {}

        with pytest.raises(
            ValueError, match='^The pattern `bar` setting of `auth_token` reader must define exactly one group$'
        ):
            RequestsWrapper(instance, init_config)


class TestAuthTokenDCOSReaderCreation:
    def test_login_url_missing(self):
        instance = {'auth_token': {'reader': {'type': 'dcos_auth'}, 'writer': {'type': 'header'}}}
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `login_url` setting of DC/OS auth token reader is required$'
        ):
            RequestsWrapper(instance, init_config)

    def test_login_url_not_string(self):
        instance = {'auth_token': {'reader': {'type': 'dcos_auth', 'login_url': {}}, 'writer': {'type': 'header'}}}
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `login_url` setting of DC/OS auth token reader must be a string$'
        ):
            RequestsWrapper(instance, init_config)

    def test_service_account_missing(self):
        instance = {
            'auth_token': {
                'reader': {'type': 'dcos_auth', 'login_url': 'https://example.com'},
                'writer': {'type': 'header'},
            }
        }
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `service_account` setting of DC/OS auth token reader is required$'
        ):
            RequestsWrapper(instance, init_config)

    def test_service_account_not_string(self):
        instance = {
            'auth_token': {
                'reader': {'type': 'dcos_auth', 'login_url': 'https://example.com', 'service_account': {}},
                'writer': {'type': 'header'},
            }
        }
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `service_account` setting of DC/OS auth token reader must be a string$'
        ):
            RequestsWrapper(instance, init_config)

    def test_private_key_path_missing(self):
        instance = {
            'auth_token': {
                'reader': {'type': 'dcos_auth', 'login_url': 'https://example.com', 'service_account': 'datadog_agent'},
                'writer': {'type': 'header'},
            }
        }
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `private_key_path` setting of DC/OS auth token reader is required$'
        ):
            RequestsWrapper(instance, init_config)

    def test_private_key_path_not_string(self):
        instance = {
            'auth_token': {
                'reader': {
                    'type': 'dcos_auth',
                    'login_url': 'https://example.com',
                    'service_account': 'datadog_agent',
                    'private_key_path': {},
                },
                'writer': {'type': 'header'},
            }
        }
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `private_key_path` setting of DC/OS auth token reader must be a string$'
        ):
            RequestsWrapper(instance, init_config)

    def test_expiration_not_integer(self):
        instance = {
            'auth_token': {
                'reader': {
                    'type': 'dcos_auth',
                    'login_url': 'https://example.com',
                    'service_account': 'datadog_agent',
                    'private_key_path': 'private-key.pem',
                    'expiration': {},
                },
                'writer': {'type': 'header'},
            }
        }
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `expiration` setting of DC/OS auth token reader must be an integer$'
        ):
            RequestsWrapper(instance, init_config)


class TestAuthTokenHeaderWriterCreation:
    def test_name_missing(self):
        instance = {'auth_token': {'reader': {'type': 'file', 'path': '/foo'}, 'writer': {'type': 'header'}}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The `name` setting of `auth_token` writer is required$'):
            RequestsWrapper(instance, init_config)

    def test_name_not_string(self):
        instance = {'auth_token': {'reader': {'type': 'file', 'path': '/foo'}, 'writer': {'type': 'header', 'name': 0}}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The `name` setting of `auth_token` writer must be a string$'):
            RequestsWrapper(instance, init_config)

    def test_value_not_string(self):
        instance = {
            'auth_token': {
                'reader': {'type': 'file', 'path': '/foo'},
                'writer': {'type': 'header', 'name': 'foo', 'value': 0},
            }
        }
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The `value` setting of `auth_token` writer must be a string$'):
            RequestsWrapper(instance, init_config)

    def test_placeholder_not_string(self):
        instance = {
            'auth_token': {
                'reader': {'type': 'file', 'path': '/foo'},
                'writer': {'type': 'header', 'name': 'foo', 'value': 'bar', 'placeholder': 0},
            }
        }
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `placeholder` setting of `auth_token` writer must be a string$'
        ):
            RequestsWrapper(instance, init_config)

    def test_placeholder_empty_string(self):
        instance = {
            'auth_token': {
                'reader': {'type': 'file', 'path': '/foo'},
                'writer': {'type': 'header', 'name': 'foo', 'value': 'bar', 'placeholder': ''},
            }
        }
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `placeholder` setting of `auth_token` writer cannot be an empty string$'
        ):
            RequestsWrapper(instance, init_config)

    def test_placeholder_not_in_value(self):
        instance = {
            'auth_token': {
                'reader': {'type': 'file', 'path': '/foo'},
                'writer': {'type': 'header', 'name': 'foo', 'value': 'bar'},
            }
        }
        init_config = {}

        with pytest.raises(
            ConfigurationError,
            match='^The `value` setting of `auth_token` writer does not contain the placeholder string `<TOKEN>`$',
        ):
            RequestsWrapper(instance, init_config)


class TestAuthTokenReadFile:
    def test_pattern_no_match(self):
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            instance = {
                'auth_token': {
                    'reader': {'type': 'file', 'path': token_file, 'pattern': 'foo(.+)'},
                    'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
                }
            }
            init_config = {}
            http = RequestsWrapper(instance, init_config)

            with mock.patch('requests.get'):
                write_file(token_file, '\nsecret\nsecret\n')

                with pytest.raises(
                    ValueError,
                    match='^{}$'.format(
                        re.escape('The pattern `foo(.+)` does not match anything in file: {}'.format(token_file))
                    ),
                ):
                    http.get('https://www.google.com')

    def test_pattern_match(self):
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            instance = {
                'auth_token': {
                    'reader': {'type': 'file', 'path': token_file, 'pattern': 'foo(.+)'},
                    'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
                }
            }
            init_config = {}
            http = RequestsWrapper(instance, init_config)

            expected_headers = {'Authorization': 'Bearer bar'}
            expected_headers.update(DEFAULT_OPTIONS['headers'])
            with mock.patch('requests.get') as get:
                write_file(token_file, '\nfoobar\nfoobaz\n')
                http.get('https://www.google.com')

                get.assert_called_with(
                    'https://www.google.com',
                    headers=expected_headers,
                    auth=None,
                    cert=None,
                    proxies=None,
                    timeout=(10.0, 10.0),
                    verify=True,
                )

                assert http.options['headers'] == expected_headers


class TestAuthTokenDCOS:
    def test_token_auth(self):
        class MockResponse:
            def __init__(self, json_data, status_code):
                self.json_data = json_data
                self.status_code = status_code

            def json(self):
                return self.json_data

            def raise_for_status(self):
                return True

        priv_key_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'dcos', 'private-key.pem')
        pub_key_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'dcos', 'public-key.pem')

        exp = 3600
        instance = {
            'auth_token': {
                'reader': {
                    'type': 'dcos_auth',
                    'login_url': 'https://leader.mesos/acs/api/v1/auth/login',
                    'service_account': 'datadog_agent',
                    'private_key_path': priv_key_path,
                    'expiration': exp,
                },
                'writer': {'type': 'header', 'name': 'Authorization', 'value': 'token=<TOKEN>'},
            }
        }
        init_config = {}

        def login(*args, **kwargs):
            if kwargs['url'] == 'https://leader.mesos/acs/api/v1/auth/login':
                json = kwargs['json']
                assert json['uid'] == 'datadog_agent'

                public_key = read_file(pub_key_path)
                decoded = jwt.decode(json['token'], public_key, algorithms='RS256')
                assert decoded['uid'] == 'datadog_agent'
                assert isinstance(decoded['exp'], int)
                assert abs(decoded['exp'] - (get_timestamp() + exp)) < 10

                return MockResponse({'token': 'auth-token'}, 200)
            return MockResponse(None, 404)

        def auth(*args, **kwargs):
            if args[0] == 'https://leader.mesos/service/some-service':
                assert kwargs['headers']['Authorization'] == 'token=auth-token'
                return MockResponse({}, 200)
            return MockResponse(None, 404)

        http = RequestsWrapper(instance, init_config)
        with mock.patch('requests.post', side_effect=login), mock.patch('requests.get', side_effect=auth):
            http.get('https://leader.mesos/service/some-service')


class TestAuthTokenWriteHeader:
    def test_default_placeholder_same_as_value(self):
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            instance = {
                'auth_token': {
                    'reader': {'type': 'file', 'path': token_file},
                    'writer': {'type': 'header', 'name': 'X-Vault-Token'},
                }
            }
            init_config = {}
            http = RequestsWrapper(instance, init_config)

            expected_headers = {'X-Vault-Token': 'foobar'}
            expected_headers.update(DEFAULT_OPTIONS['headers'])
            with mock.patch('requests.get') as get:
                write_file(token_file, '\nfoobar\n')
                http.get('https://www.google.com')

                get.assert_called_with(
                    'https://www.google.com',
                    headers=expected_headers,
                    auth=None,
                    cert=None,
                    proxies=None,
                    timeout=(10.0, 10.0),
                    verify=True,
                )

                assert http.options['headers'] == expected_headers


class TestAuthTokenFileReaderWithHeaderWriter:
    def test_read_before_first_request(self):
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            instance = {
                'auth_token': {
                    'reader': {'type': 'file', 'path': token_file},
                    'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
                }
            }
            init_config = {}
            http = RequestsWrapper(instance, init_config)

            expected_headers = {'Authorization': 'Bearer secret1'}
            expected_headers.update(DEFAULT_OPTIONS['headers'])
            with mock.patch('requests.get') as get:
                write_file(token_file, '\nsecret1\n')
                http.get('https://www.google.com')

                get.assert_called_with(
                    'https://www.google.com',
                    headers=expected_headers,
                    auth=None,
                    cert=None,
                    proxies=None,
                    timeout=(10.0, 10.0),
                    verify=True,
                )

                assert http.options['headers'] == expected_headers

                # Should use cached token
                write_file(token_file, '\nsecret2\n')
                http.get('https://www.google.com')

                get.assert_called_with(
                    'https://www.google.com',
                    headers=expected_headers,
                    auth=None,
                    cert=None,
                    proxies=None,
                    timeout=(10.0, 10.0),
                    verify=True,
                )

                assert http.options['headers'] == expected_headers

    def test_refresh_after_connection_error(self):
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            instance = {
                'auth_token': {
                    'reader': {'type': 'file', 'path': token_file},
                    'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
                }
            }
            init_config = {}
            http = RequestsWrapper(instance, init_config)

            with mock.patch('requests.get'):
                write_file(token_file, '\nsecret1\n')
                http.get('https://www.google.com')

            # TODO: use nonlocal when we drop Python 2 support
            counter = {'errors': 0}

            def raise_error_once(*args, **kwargs):
                counter['errors'] += 1
                if counter['errors'] <= 1:
                    raise Exception

            expected_headers = {'Authorization': 'Bearer secret2'}
            expected_headers.update(DEFAULT_OPTIONS['headers'])
            with mock.patch('requests.get', side_effect=raise_error_once) as get:
                write_file(token_file, '\nsecret2\n')

                http.get('https://www.google.com')

                get.assert_called_with(
                    'https://www.google.com',
                    headers=expected_headers,
                    auth=None,
                    cert=None,
                    proxies=None,
                    timeout=(10.0, 10.0),
                    verify=True,
                )

                assert http.options['headers'] == expected_headers

    def test_refresh_after_bad_status_code(self):
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            instance = {
                'auth_token': {
                    'reader': {'type': 'file', 'path': token_file},
                    'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
                }
            }
            init_config = {}
            http = RequestsWrapper(instance, init_config)

            with mock.patch('requests.get'):
                write_file(token_file, '\nsecret1\n')
                http.get('https://www.google.com')

            def error():
                raise Exception()

            expected_headers = {'Authorization': 'Bearer secret2'}
            expected_headers.update(DEFAULT_OPTIONS['headers'])
            with mock.patch('requests.get', return_value=mock.MagicMock(raise_for_status=error)) as get:
                write_file(token_file, '\nsecret2\n')
                http.get('https://www.google.com')

                get.assert_called_with(
                    'https://www.google.com',
                    headers=expected_headers,
                    auth=None,
                    cert=None,
                    proxies=None,
                    timeout=(10.0, 10.0),
                    verify=True,
                )

                assert http.options['headers'] == expected_headers


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
    def test_no_proxy_single_wildcard(self, socks5_proxy):
        instance = {'proxy': {'http': 'http://1.2.3.4:567', 'no_proxy': '.foo,bar,*'}}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        http.get('http://www.example.org')
        http.get('http://www.example.com')
        http.get('http://127.0.0.9')

    @pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
    def test_no_proxy_domain(self, socks5_proxy):
        instance = {'proxy': {'http': 'http://1.2.3.4:567', 'no_proxy': '.google.com,*.example.org,example.com,9'}}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        # no_proxy match: .google.com
        http.get('http://www.google.com')

        # no_proxy match: *.example.org
        http.get('http://www.example.org')

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

    def test_default_no_ignore(self, caplog):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, level, message in caplog.record_tuples:
            if level == logging.WARNING and message == expected_message:
                break
        else:
            raise AssertionError('Expected WARNING log with message `{}`'.format(expected_message))

    def test_default_no_ignore_http(self, caplog):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            http.get('http://www.google.com', verify=False)

        assert sum(1 for _, level, _ in caplog.record_tuples if level == logging.WARNING) == 0

    def test_ignore(self, caplog):
        instance = {'tls_ignore_warning': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, _, message in caplog.record_tuples:
            assert message != expected_message

    def test_default_no_ignore_session(self, caplog):
        instance = {'persist_connections': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, level, message in caplog.record_tuples:
            if level == logging.WARNING and message == expected_message:
                break
        else:
            raise AssertionError('Expected WARNING log with message `{}`'.format(expected_message))

    def test_ignore_session(self, caplog):
        instance = {'tls_ignore_warning': True, 'persist_connections': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, _, message in caplog.record_tuples:
            assert message != expected_message

    def test_init_ignore(self, caplog):
        instance = {}
        init_config = {'tls_ignore_warning': True}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, _, message in caplog.record_tuples:
            assert message != expected_message

    def test_default_init_no_ignore(self, caplog):
        instance = {}
        init_config = {'tls_ignore_warning': False}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, level, message in caplog.record_tuples:
            if level == logging.WARNING and message == expected_message:
                break
        else:
            raise AssertionError('Expected WARNING log with message `{}`'.format(expected_message))

    def test_instance_ignore(self, caplog):
        instance = {'tls_ignore_warning': True}
        init_config = {'tls_ignore_warning': False}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, _, message in caplog.record_tuples:
            assert message != expected_message

    def test_instance_no_ignore(self, caplog):
        instance = {'tls_ignore_warning': False}
        init_config = {'tls_ignore_warning': True}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, level, message in caplog.record_tuples:
            if level == logging.WARNING and message == expected_message:
                break
        else:
            raise AssertionError('Expected WARNING log with message `{}`'.format(expected_message))


class TestUnixDomainSocket:
    @pytest.mark.parametrize(
        'value, expected',
        [
            pytest.param('http://example.org', False, id='non-uds-url'),
            pytest.param('unix:///var/run/test.sock/info', True, id='unquoted'),
            pytest.param('unix://%2Fvar%2Frun%2Ftest.sock', True, id='quoted'),
        ],
    )
    def test_is_uds_url(self, value, expected):
        # type: (str, bool) -> None
        assert is_uds_url(value) == expected

    @pytest.mark.parametrize(
        'value, expected',
        [
            pytest.param('http://example.org', 'http://example.org', id='non-uds-url'),
            pytest.param('unix:///var/run/test.sock/info', 'unix://%2Fvar%2Frun%2Ftest.sock/info', id='uds-url'),
            pytest.param('unix:///var/run/test.sock', 'unix://%2Fvar%2Frun%2Ftest.sock', id='uds-url-no-path'),
            pytest.param(
                'unix://%2Fvar%2Frun%2Ftest.sock/info', 'unix://%2Fvar%2Frun%2Ftest.sock/info', id='already-quoted'
            ),
        ],
    )
    def test_quote_uds_url(self, value, expected):
        # type: (str, str) -> None
        assert quote_uds_url(value) == expected

    def test_adapter_mounted(self):
        # type: () -> None
        http = RequestsWrapper({}, {})
        url = 'unix:///var/run/test.sock'
        adapter = http.session.get_adapter(url=url)
        assert adapter is not None
        assert isinstance(adapter, requests_unixsocket.UnixAdapter)

    @pytest.mark.skipif(ON_WINDOWS, reason='AF_UNIX not supported by Python on Windows yet')
    def test_uds_request(self, uds_path):
        # type: (str) -> None
        http = RequestsWrapper({}, {})
        url = 'unix://{}'.format(uds_path)
        response = http.get(url)
        assert response.status_code == 200
        assert response.text == 'Hello, World!'


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

    def test_options(self):
        http = RequestsWrapper({}, {})

        with mock.patch('requests.options'):
            http.options_method('https://www.google.com')
            requests.options.assert_called_once_with('https://www.google.com', **http.options)

    def test_options_session(self):
        http = RequestsWrapper({'persist_connections': True}, {})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.options_method('https://www.google.com')
            http.session.options.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)

    def test_options_option_override(self):
        http = RequestsWrapper({}, {})
        options = http.options.copy()
        options['auth'] = ('user', 'pass')

        with mock.patch('requests.options'):
            http.options_method('https://www.google.com', auth=options['auth'])
            requests.options.assert_called_once_with('https://www.google.com', **options)

    def test_options_session_option_override(self):
        http = RequestsWrapper({}, {})
        options = DEFAULT_OPTIONS.copy()
        options.update({'auth': ('user', 'pass')})

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.options_method('https://www.google.com', persist=True, auth=options['auth'])
            http.session.options.assert_called_once_with('https://www.google.com', **options)


class TestIntegration:
    def test_session_timeout(self):
        http = RequestsWrapper({'persist_connections': True}, {'timeout': 0.08})
        with pytest.raises(requests.exceptions.Timeout):
            http.get('https://httpbin.org/delay/0.10')
