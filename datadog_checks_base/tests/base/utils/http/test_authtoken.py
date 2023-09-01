# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

import jwt
import mock
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.base.utils.time import get_timestamp
from datadog_checks.dev import TempDir
from datadog_checks.dev.fs import read_file, write_file
from datadog_checks.dev.http import MockResponse

from .common import DEFAULT_OPTIONS, FIXTURE_PATH

pytestmark = [pytest.mark.unit]


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
            ConfigurationError, match='^Unknown `auth_token` reader type, must be one of: dcos_auth, file, oauth$'
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


class TestAuthTokenOAuthReaderCreation:
    def test_url_missing(self):
        instance = {'auth_token': {'reader': {'type': 'oauth'}, 'writer': {'type': 'header'}}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The `url` setting of `auth_token` reader is required$'):
            RequestsWrapper(instance, init_config)

    def test_url_not_string(self):
        instance = {'auth_token': {'reader': {'type': 'oauth', 'url': {}}, 'writer': {'type': 'header'}}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The `url` setting of `auth_token` reader must be a string$'):
            RequestsWrapper(instance, init_config)

    def test_client_id_missing(self):
        instance = {'auth_token': {'reader': {'type': 'oauth', 'url': 'foo'}, 'writer': {'type': 'header'}}}
        init_config = {}

        with pytest.raises(ConfigurationError, match='^The `client_id` setting of `auth_token` reader is required$'):
            RequestsWrapper(instance, init_config)

    def test_client_id_not_string(self):
        instance = {
            'auth_token': {'reader': {'type': 'oauth', 'url': 'foo', 'client_id': {}}, 'writer': {'type': 'header'}}
        }
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `client_id` setting of `auth_token` reader must be a string$'
        ):
            RequestsWrapper(instance, init_config)

    def test_client_secret_missing(self):
        instance = {
            'auth_token': {'reader': {'type': 'oauth', 'url': 'foo', 'client_id': 'bar'}, 'writer': {'type': 'header'}}
        }
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `client_secret` setting of `auth_token` reader is required$'
        ):
            RequestsWrapper(instance, init_config)

    def test_client_secret_not_string(self):
        instance = {
            'auth_token': {
                'reader': {'type': 'oauth', 'url': 'foo', 'client_id': 'bar', 'client_secret': {}},
                'writer': {'type': 'header'},
            }
        }
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `client_secret` setting of `auth_token` reader must be a string$'
        ):
            RequestsWrapper(instance, init_config)

    def test_basic_auth_not_boolean(self):
        instance = {
            'auth_token': {
                'reader': {'type': 'oauth', 'url': 'foo', 'client_id': 'bar', 'client_secret': 'baz', 'basic_auth': {}},
                'writer': {'type': 'header'},
            }
        }
        init_config = {}

        with pytest.raises(
            ConfigurationError, match='^The `basic_auth` setting of `auth_token` reader must be a boolean$'
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
                    allow_redirects=True,
                )

                assert http.options['headers'] == expected_headers


class TestAuthTokenOAuth:
    def test_failure(self):
        instance = {
            'auth_token': {
                'reader': {'type': 'oauth', 'url': 'foo', 'client_id': 'bar', 'client_secret': 'baz'},
                'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
            }
        }
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        expected_headers = {'Authorization': 'Bearer foo'}
        expected_headers.update(DEFAULT_OPTIONS['headers'])

        class MockOAuth2Session(object):
            def __init__(self, *args, **kwargs):
                pass

            def fetch_token(self, *args, **kwargs):
                return {'error': 'unauthorized_client'}

        with mock.patch('requests.get'), mock.patch('oauthlib.oauth2.BackendApplicationClient'), mock.patch(
            'requests_oauthlib.OAuth2Session', side_effect=MockOAuth2Session
        ):
            with pytest.raises(Exception, match='OAuth2 client credentials grant error: unauthorized_client'):
                http.get('https://www.google.com')

    def test_success(self):
        instance = {
            'auth_token': {
                'reader': {'type': 'oauth', 'url': 'foo', 'client_id': 'bar', 'client_secret': 'baz'},
                'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
            }
        }
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        expected_headers = {'Authorization': 'Bearer foo'}
        expected_headers.update(DEFAULT_OPTIONS['headers'])

        class MockOAuth2Session(object):
            def __init__(self, *args, **kwargs):
                pass

            def fetch_token(self, *args, **kwargs):
                return {'access_token': 'foo', 'expires_in': 9000}

        with mock.patch('requests.get') as get, mock.patch('oauthlib.oauth2.BackendApplicationClient'), mock.patch(
            'requests_oauthlib.OAuth2Session', side_effect=MockOAuth2Session
        ):
            http.get('https://www.google.com')

            get.assert_called_with(
                'https://www.google.com',
                headers=expected_headers,
                auth=None,
                cert=None,
                proxies=None,
                timeout=(10.0, 10.0),
                verify=True,
                allow_redirects=True,
            )

            assert http.options['headers'] == expected_headers


class TestAuthTokenDCOS:
    def test_token_auth(self):
        priv_key_path = os.path.join(FIXTURE_PATH, 'dcos', 'private-key.pem')
        pub_key_path = os.path.join(FIXTURE_PATH, 'dcos', 'public-key.pem')

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

                return MockResponse(json_data={'token': 'auth-token'})
            return MockResponse(status_code=404)

        def auth(*args, **kwargs):
            if args[0] == 'https://leader.mesos/service/some-service':
                assert kwargs['headers']['Authorization'] == 'token=auth-token'
                return MockResponse(json_data={})
            return MockResponse(status_code=404)

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
                    allow_redirects=True,
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
                    allow_redirects=True,
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
                    allow_redirects=True,
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

                return MockResponse()

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
                    allow_redirects=True,
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
                    allow_redirects=True,
                )

                assert http.options['headers'] == expected_headers
