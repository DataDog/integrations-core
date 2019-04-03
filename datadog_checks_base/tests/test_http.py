# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import OrderedDict

import mock
import pytest
import requests
from requests.exceptions import ConnectTimeout, ProxyError
from six import iteritems
from urllib3.exceptions import InsecureRequestWarning

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http import STANDARD_FIELDS, RequestsWrapper
from datadog_checks.dev import EnvVars

pytestmark = pytest.mark.http


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
        assert 0 < http.options['timeout'] % 3 <= 1

    def test_config_timeout(self):
        instance = {'timeout': 24.5}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['timeout'] == 24.5


class TestHeaders:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['headers'] is None

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


class TestVerify:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['verify'] is True

    def test_config_verify(self):
        instance = {'ssl_verify': False}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['verify'] is False

    def test_config_ca_cert(self):
        instance = {'ssl_ca_cert': 'ca_cert'}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['verify'] == 'ca_cert'

    def test_config_verify_and_ca_cert(self):
        instance = {'ssl_verify': True, 'ssl_ca_cert': 'ca_cert'}
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
        instance = {'ssl_cert': 'cert'}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['cert'] == 'cert'

    def test_config_cert_and_private_key(self):
        instance = {'ssl_cert': 'cert', 'ssl_private_key': 'key'}
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

        setattr(http.no_proxy_uris, '__iter__', lambda self, *args, **kwargs: iter([]))
        setattr(http.no_proxy_uris, '__bool__', lambda self, *args, **kwargs: True)
        # TODO: Remove with Python 2
        setattr(http.no_proxy_uris, '__nonzero__', lambda self, *args, **kwargs: True)

        http.get('https://www.google.com')


class TestIgnoreSSLWarning:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.ignore_ssl_warning is False

    def test_config_flag(self):
        instance = {'ssl_ignore_warning': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.ignore_ssl_warning is True

    def test_default_no_ignore(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with pytest.warns(InsecureRequestWarning):
            http.get('https://www.google.com', verify=False)

    def test_ignore(self):
        instance = {'ssl_ignore_warning': True}
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
        instance = {'ssl_ignore_warning': True, 'persist_connections': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with pytest.warns(None) as record:
            http.get('https://www.google.com', verify=False)

        assert all(not issubclass(warning.category, InsecureRequestWarning) for warning in record)


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

        assert http.options['timeout'] == STANDARD_FIELDS['timeout']

    def test_invert(self):
        instance = {'disable_ssl_validation': False}
        init_config = {}
        remapper = {'disable_ssl_validation': {'name': 'ssl_verify', 'default': False, 'invert': True}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.options['verify'] is True

    def test_standard_override(self):
        instance = {'disable_ssl_validation': True, 'ssl_verify': False}
        init_config = {}
        remapper = {'disable_ssl_validation': {'name': 'ssl_verify', 'default': False, 'invert': True}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.options['verify'] is False

    def test_unknown_name_default(self):
        instance = {}
        init_config = {}
        remapper = {'verify_ssl': {'name': 'verify', 'default': False}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.options['verify'] is True


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
            http.session.get.assert_called_once_with('https://www.google.com')

    def test_get_option_override(self):
        http = RequestsWrapper({}, {})
        options = http.options.copy()
        options['auth'] = ('user', 'pass')

        with mock.patch('requests.get'):
            http.get('https://www.google.com', auth=options['auth'])
            requests.get.assert_called_once_with('https://www.google.com', **options)

    def test_get_session_option_override(self):
        http = RequestsWrapper({}, {})
        options = {'auth': ('user', 'pass')}

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
            http.session.post.assert_called_once_with('https://www.google.com')

    def test_post_option_override(self):
        http = RequestsWrapper({}, {})
        options = http.options.copy()
        options['auth'] = ('user', 'pass')

        with mock.patch('requests.post'):
            http.post('https://www.google.com', auth=options['auth'])
            requests.post.assert_called_once_with('https://www.google.com', **options)

    def test_post_session_option_override(self):
        http = RequestsWrapper({}, {})
        options = {'auth': ('user', 'pass')}

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
            http.session.head.assert_called_once_with('https://www.google.com')

    def test_head_option_override(self):
        http = RequestsWrapper({}, {})
        options = http.options.copy()
        options['auth'] = ('user', 'pass')

        with mock.patch('requests.head'):
            http.head('https://www.google.com', auth=options['auth'])
            requests.head.assert_called_once_with('https://www.google.com', **options)

    def test_head_session_option_override(self):
        http = RequestsWrapper({}, {})
        options = {'auth': ('user', 'pass')}

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
            http.session.put.assert_called_once_with('https://www.google.com')

    def test_put_option_override(self):
        http = RequestsWrapper({}, {})
        options = http.options.copy()
        options['auth'] = ('user', 'pass')

        with mock.patch('requests.put'):
            http.put('https://www.google.com', auth=options['auth'])
            requests.put.assert_called_once_with('https://www.google.com', **options)

    def test_put_session_option_override(self):
        http = RequestsWrapper({}, {})
        options = {'auth': ('user', 'pass')}

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
            http.session.patch.assert_called_once_with('https://www.google.com')

    def test_patch_option_override(self):
        http = RequestsWrapper({}, {})
        options = http.options.copy()
        options['auth'] = ('user', 'pass')

        with mock.patch('requests.patch'):
            http.patch('https://www.google.com', auth=options['auth'])
            requests.patch.assert_called_once_with('https://www.google.com', **options)

    def test_patch_session_option_override(self):
        http = RequestsWrapper({}, {})
        options = {'auth': ('user', 'pass')}

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
            http.session.delete.assert_called_once_with('https://www.google.com')

    def test_delete_option_override(self):
        http = RequestsWrapper({}, {})
        options = http.options.copy()
        options['auth'] = ('user', 'pass')

        with mock.patch('requests.delete'):
            http.delete('https://www.google.com', auth=options['auth'])
            requests.delete.assert_called_once_with('https://www.google.com', **options)

    def test_delete_session_option_override(self):
        http = RequestsWrapper({}, {})
        options = {'auth': ('user', 'pass')}

        with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
            http.delete('https://www.google.com', persist=True, auth=options['auth'])
            http.session.delete.assert_called_once_with('https://www.google.com', **options)
