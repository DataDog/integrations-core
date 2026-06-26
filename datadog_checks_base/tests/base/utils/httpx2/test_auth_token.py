# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
from urllib.parse import parse_qs

import httpx2
import mock
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.base.utils.httpx2 import DEFAULT_EXPIRATION, HTTPX2Wrapper
from datadog_checks.dev import TempDir
from datadog_checks.dev.fs import write_file

pytestmark = [pytest.mark.unit]

OAUTH_CLIENT_BUILDER = 'datadog_checks.base.utils.httpx2._build_oauth_client'
GET_TIMESTAMP = 'datadog_checks.base.utils.httpx2.get_timestamp'


def oauth_transport(token_response, captured=None):
    """A MockTransport that returns token_response as JSON and optionally records the token request."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        if captured is not None:
            _ = request.content
            captured.append(request)
        return httpx2.Response(200, json=token_response)

    return httpx2.MockTransport(handler)


def patch_oauth_client(transport):
    """Patch the standalone OAuth client builder so each fetch gets a fresh client over the given transport."""
    return mock.patch(OAUTH_CLIENT_BUILDER, side_effect=lambda: httpx2.Client(transport=transport))


class TestAuthTokenHandlerCreation:
    def test_not_mapping(self):
        with pytest.raises(ConfigurationError, match='^The `auth_token` field must be a mapping$'):
            HTTPX2Wrapper({'auth_token': ''}, {})

    def test_no_reader(self):
        with pytest.raises(
            ConfigurationError, match='^The `auth_token` field must define both `reader` and `writer` settings$'
        ):
            HTTPX2Wrapper({'auth_token': {'writer': {}}}, {})

    def test_no_writer(self):
        with pytest.raises(
            ConfigurationError, match='^The `auth_token` field must define both `reader` and `writer` settings$'
        ):
            HTTPX2Wrapper({'auth_token': {'reader': {}}}, {})

    def test_reader_config_not_mapping(self):
        with pytest.raises(ConfigurationError, match='^The `reader` settings of field `auth_token` must be a mapping$'):
            HTTPX2Wrapper({'auth_token': {'reader': '', 'writer': {}}}, {})

    def test_writer_config_not_mapping(self):
        with pytest.raises(ConfigurationError, match='^The `writer` settings of field `auth_token` must be a mapping$'):
            HTTPX2Wrapper({'auth_token': {'reader': {}, 'writer': ''}}, {})

    def test_reader_type_missing(self):
        with pytest.raises(ConfigurationError, match='^The reader `type` of field `auth_token` is required$'):
            HTTPX2Wrapper({'auth_token': {'reader': {}, 'writer': {}}}, {})

    def test_reader_type_not_string(self):
        with pytest.raises(ConfigurationError, match='^The reader `type` of field `auth_token` must be a string$'):
            HTTPX2Wrapper({'auth_token': {'reader': {'type': {}}, 'writer': {}}}, {})

    def test_reader_type_unknown(self):
        # Deliberate divergence from RequestsWrapper: dcos_auth is deferred, so it is absent from this list.
        with pytest.raises(ConfigurationError, match='^Unknown `auth_token` reader type, must be one of: file, oauth$'):
            HTTPX2Wrapper({'auth_token': {'reader': {'type': 'foo'}, 'writer': {}}}, {})

    def test_writer_type_missing(self):
        with pytest.raises(ConfigurationError, match='^The writer `type` of field `auth_token` is required$'):
            HTTPX2Wrapper({'auth_token': {'reader': {'type': 'file'}, 'writer': {}}}, {})

    def test_writer_type_not_string(self):
        with pytest.raises(ConfigurationError, match='^The writer `type` of field `auth_token` must be a string$'):
            HTTPX2Wrapper({'auth_token': {'reader': {'type': 'file'}, 'writer': {'type': {}}}}, {})

    def test_writer_type_unknown(self):
        with pytest.raises(ConfigurationError, match='^Unknown `auth_token` writer type, must be one of: header$'):
            HTTPX2Wrapper({'auth_token': {'reader': {'type': 'file'}, 'writer': {'type': 'foo'}}}, {})


class TestAuthTokenDeferredReaders:
    def test_dcos_auth_deferred(self):
        # dcos_auth has a named home: a clear deferred error rather than the generic unknown-type message.
        with pytest.raises(ConfigurationError, match='dcos_auth'):
            HTTPX2Wrapper({'auth_token': {'reader': {'type': 'dcos_auth'}, 'writer': {'type': 'header'}}}, {})


class TestAuthTokenFileReaderCreation:
    def test_path_missing(self):
        with pytest.raises(ConfigurationError, match='^The `path` setting of `auth_token` reader is required$'):
            HTTPX2Wrapper({'auth_token': {'reader': {'type': 'file'}, 'writer': {'type': 'header'}}}, {})

    def test_path_not_string(self):
        with pytest.raises(ConfigurationError, match='^The `path` setting of `auth_token` reader must be a string$'):
            HTTPX2Wrapper({'auth_token': {'reader': {'type': 'file', 'path': {}}, 'writer': {'type': 'header'}}}, {})

    def test_pattern_not_string(self):
        with pytest.raises(ConfigurationError, match='^The `pattern` setting of `auth_token` reader must be a string$'):
            HTTPX2Wrapper(
                {
                    'auth_token': {
                        'reader': {'type': 'file', 'path': '/foo', 'pattern': 0},
                        'writer': {'type': 'header'},
                    }
                },
                {},
            )

    def test_pattern_no_groups(self):
        with pytest.raises(
            ValueError, match='^The pattern `bar` setting of `auth_token` reader must define exactly one group$'
        ):
            HTTPX2Wrapper(
                {
                    'auth_token': {
                        'reader': {'type': 'file', 'path': '/foo', 'pattern': 'bar'},
                        'writer': {'type': 'header'},
                    }
                },
                {},
            )


class TestAuthTokenOAuthReaderCreation:
    def test_url_missing(self):
        with pytest.raises(ConfigurationError, match='^The `url` setting of `auth_token` reader is required$'):
            HTTPX2Wrapper({'auth_token': {'reader': {'type': 'oauth'}, 'writer': {'type': 'header'}}}, {})

    def test_url_not_string(self):
        with pytest.raises(ConfigurationError, match='^The `url` setting of `auth_token` reader must be a string$'):
            HTTPX2Wrapper({'auth_token': {'reader': {'type': 'oauth', 'url': {}}, 'writer': {'type': 'header'}}}, {})

    def test_client_id_missing(self):
        with pytest.raises(ConfigurationError, match='^The `client_id` setting of `auth_token` reader is required$'):
            HTTPX2Wrapper({'auth_token': {'reader': {'type': 'oauth', 'url': 'foo'}, 'writer': {'type': 'header'}}}, {})

    def test_client_id_not_string(self):
        with pytest.raises(
            ConfigurationError, match='^The `client_id` setting of `auth_token` reader must be a string$'
        ):
            HTTPX2Wrapper(
                {
                    'auth_token': {
                        'reader': {'type': 'oauth', 'url': 'foo', 'client_id': {}},
                        'writer': {'type': 'header'},
                    }
                },
                {},
            )

    def test_client_secret_missing(self):
        with pytest.raises(
            ConfigurationError, match='^The `client_secret` setting of `auth_token` reader is required$'
        ):
            HTTPX2Wrapper(
                {
                    'auth_token': {
                        'reader': {'type': 'oauth', 'url': 'foo', 'client_id': 'bar'},
                        'writer': {'type': 'header'},
                    }
                },
                {},
            )

    def test_client_secret_not_string(self):
        with pytest.raises(
            ConfigurationError, match='^The `client_secret` setting of `auth_token` reader must be a string$'
        ):
            HTTPX2Wrapper(
                {
                    'auth_token': {
                        'reader': {'type': 'oauth', 'url': 'foo', 'client_id': 'bar', 'client_secret': {}},
                        'writer': {'type': 'header'},
                    }
                },
                {},
            )

    def test_basic_auth_not_boolean(self):
        with pytest.raises(
            ConfigurationError, match='^The `basic_auth` setting of `auth_token` reader must be a boolean$'
        ):
            HTTPX2Wrapper(
                {
                    'auth_token': {
                        'reader': {
                            'type': 'oauth',
                            'url': 'foo',
                            'client_id': 'bar',
                            'client_secret': 'baz',
                            'basic_auth': {},
                        },
                        'writer': {'type': 'header'},
                    }
                },
                {},
            )


class TestAuthTokenHeaderWriterCreation:
    def test_name_missing(self):
        with pytest.raises(ConfigurationError, match='^The `name` setting of `auth_token` writer is required$'):
            HTTPX2Wrapper(
                {'auth_token': {'reader': {'type': 'file', 'path': '/foo'}, 'writer': {'type': 'header'}}}, {}
            )

    def test_name_not_string(self):
        with pytest.raises(ConfigurationError, match='^The `name` setting of `auth_token` writer must be a string$'):
            HTTPX2Wrapper(
                {'auth_token': {'reader': {'type': 'file', 'path': '/foo'}, 'writer': {'type': 'header', 'name': 0}}},
                {},
            )

    def test_value_not_string(self):
        with pytest.raises(ConfigurationError, match='^The `value` setting of `auth_token` writer must be a string$'):
            HTTPX2Wrapper(
                {
                    'auth_token': {
                        'reader': {'type': 'file', 'path': '/foo'},
                        'writer': {'type': 'header', 'name': 'foo', 'value': 0},
                    }
                },
                {},
            )

    def test_placeholder_not_string(self):
        with pytest.raises(
            ConfigurationError, match='^The `placeholder` setting of `auth_token` writer must be a string$'
        ):
            HTTPX2Wrapper(
                {
                    'auth_token': {
                        'reader': {'type': 'file', 'path': '/foo'},
                        'writer': {'type': 'header', 'name': 'foo', 'value': 'bar', 'placeholder': 0},
                    }
                },
                {},
            )

    def test_placeholder_empty_string(self):
        with pytest.raises(
            ConfigurationError, match='^The `placeholder` setting of `auth_token` writer cannot be an empty string$'
        ):
            HTTPX2Wrapper(
                {
                    'auth_token': {
                        'reader': {'type': 'file', 'path': '/foo'},
                        'writer': {'type': 'header', 'name': 'foo', 'value': 'bar', 'placeholder': ''},
                    }
                },
                {},
            )

    def test_placeholder_not_in_value(self):
        with pytest.raises(
            ConfigurationError,
            match='^The `value` setting of `auth_token` writer does not contain the placeholder string `<TOKEN>`$',
        ):
            HTTPX2Wrapper(
                {
                    'auth_token': {
                        'reader': {'type': 'file', 'path': '/foo'},
                        'writer': {'type': 'header', 'name': 'foo', 'value': 'bar'},
                    }
                },
                {},
            )


class TestAuthTokenReadFile:
    def test_pattern_no_match(self, capturing_transport):
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            instance = {
                'auth_token': {
                    'reader': {'type': 'file', 'path': token_file, 'pattern': 'foo(.+)'},
                    'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
                }
            }
            http = HTTPX2Wrapper(instance, {}, transport=capturing_transport)
            write_file(token_file, '\nsecret\nsecret\n')

            with pytest.raises(
                ValueError,
                match='^{}$'.format(
                    re.escape('The pattern `foo(.+)` does not match anything in file: {}'.format(token_file))
                ),
            ):
                http.get('https://www.example.com')

    def test_pattern_match(self, capturing_transport, captured_requests):
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            instance = {
                'auth_token': {
                    'reader': {'type': 'file', 'path': token_file, 'pattern': 'foo(.+)'},
                    'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
                }
            }
            http = HTTPX2Wrapper(instance, {}, transport=capturing_transport)
            write_file(token_file, '\nfoobar\nfoobaz\n')
            http.get('https://www.example.com')

            assert captured_requests[-1].headers['Authorization'] == 'Bearer bar'
            assert http.get_header('Authorization') == 'Bearer bar'

    def test_default_placeholder_same_as_value(self, capturing_transport, captured_requests):
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            instance = {
                'auth_token': {
                    'reader': {'type': 'file', 'path': token_file},
                    'writer': {'type': 'header', 'name': 'X-Vault-Token'},
                }
            }
            http = HTTPX2Wrapper(instance, {}, transport=capturing_transport)
            write_file(token_file, '\nfoobar\n')
            http.get('https://www.example.com')

            assert captured_requests[-1].headers['X-Vault-Token'] == 'foobar'

    def test_read_before_first_request_and_cache(self, capturing_transport, captured_requests):
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            instance = {
                'auth_token': {
                    'reader': {'type': 'file', 'path': token_file},
                    'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
                }
            }
            http = HTTPX2Wrapper(instance, {}, transport=capturing_transport)

            write_file(token_file, '\nsecret1\n')
            http.get('https://www.example.com')
            assert captured_requests[-1].headers['Authorization'] == 'Bearer secret1'

            # A second request reuses the cached token even though the file changed.
            write_file(token_file, '\nsecret2\n')
            http.get('https://www.example.com')
            assert captured_requests[-1].headers['Authorization'] == 'Bearer secret1'


class TestAuthTokenOAuth:
    @pytest.mark.parametrize(
        'token_response, expected_expiration',
        [
            pytest.param({'access_token': 'foo', 'expires_in': 9000}, 9000, id='With expires_in'),
            pytest.param({'access_token': 'foo'}, DEFAULT_EXPIRATION, id='Without expires_in'),
            pytest.param(
                {'access_token': 'foo', 'expires_in': 'two minutes'}, DEFAULT_EXPIRATION, id='With string expires_in'
            ),
            pytest.param({'access_token': 'foo', 'expires_in': '3600'}, 3600, id='With numeric string expires_in'),
            pytest.param(
                {'access_token': 'foo', 'expires_in': [1, 2, 3]}, DEFAULT_EXPIRATION, id='With list expires_in'
            ),
        ],
    )
    def test_success(self, capturing_transport, captured_requests, token_response, expected_expiration):
        instance = {
            'auth_token': {
                'reader': {
                    'type': 'oauth',
                    'url': 'http://example.com/token',
                    'client_id': 'bar',
                    'client_secret': 'baz',
                },
                'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
            }
        }
        http = HTTPX2Wrapper(instance, {}, transport=capturing_transport)

        with patch_oauth_client(oauth_transport(token_response)), mock.patch(GET_TIMESTAMP, return_value=0):
            http.get('https://www.example.com')

        assert captured_requests[-1].headers['Authorization'] == 'Bearer foo'
        assert http.auth_token_handler.reader._expiration == expected_expiration

    def test_failure(self, capturing_transport):
        instance = {
            'auth_token': {
                'reader': {
                    'type': 'oauth',
                    'url': 'http://example.com/token',
                    'client_id': 'bar',
                    'client_secret': 'baz',
                },
                'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
            }
        }
        http = HTTPX2Wrapper(instance, {}, transport=capturing_transport)

        with patch_oauth_client(oauth_transport({'error': 'unauthorized_client'})):
            with pytest.raises(Exception, match='OAuth2 client credentials grant error: unauthorized_client'):
                http.get('https://www.example.com')

    def test_options_passthrough(self, capturing_transport, captured_requests):
        oauth_requests = []
        instance = {
            'auth_token': {
                'reader': {
                    'type': 'oauth',
                    'url': 'http://example.com/token',
                    'client_id': 'bar',
                    'client_secret': 'baz',
                    'options': {'audience': 'http://example.com', 'scope': 'openid'},
                },
                'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
            }
        }
        http = HTTPX2Wrapper(instance, {}, transport=capturing_transport)

        with patch_oauth_client(oauth_transport({'access_token': 'foo', 'expires_in': 9000}, captured=oauth_requests)):
            http.get('https://www.example.com')

        body = parse_qs(oauth_requests[-1].content.decode('utf-8'))
        assert body['grant_type'] == ['client_credentials']
        assert body['scope'] == ['openid']
        assert body['audience'] == ['http://example.com']
        assert captured_requests[-1].headers['Authorization'] == 'Bearer foo'


class _RenewTransport(httpx2.BaseTransport):
    """Succeed on every send except a chosen call index, which fails (exception) or returns a set response."""

    def __init__(self, fail_on_call, failure):
        self._fail_on_call = fail_on_call
        self._failure = failure
        self.calls = 0
        self.requests = []

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        self.calls += 1
        self.requests.append(request)
        if self.calls == self._fail_on_call:
            if isinstance(self._failure, Exception):
                raise self._failure
            return self._failure
        return httpx2.Response(200, json={'ok': True})


class _ClosableStream(httpx2.SyncByteStream):
    """A streamed body that records when it is closed, so the renew path's close is observable."""

    def __init__(self, closed_flag):
        self._closed_flag = closed_flag

    def __iter__(self):
        yield b'unauthorized'

    def close(self):
        self._closed_flag['value'] = True


class TestAuthTokenRenew:
    def _file_instance(self, token_file):
        return {
            'auth_token': {
                'reader': {'type': 'file', 'path': token_file},
                'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
            }
        }

    def test_renew_on_connection_error(self):
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            write_file(token_file, '\nsecret1\n')
            transport = _RenewTransport(fail_on_call=2, failure=httpx2.ConnectError('boom'))
            http = HTTPX2Wrapper(self._file_instance(token_file), {}, transport=transport)

            # First request caches secret1; the second sends the cached token, fails, then renews.
            http.get('https://www.example.com')
            write_file(token_file, '\nsecret2\n')
            response = http.get('https://www.example.com')

            assert transport.requests[1].headers['Authorization'] == 'Bearer secret1'
            assert transport.requests[-1].headers['Authorization'] == 'Bearer secret2'
            # The retry response must be a usable adapter with a readable body.
            assert response.json() == {'ok': True}

    def test_renew_on_bad_status_closes_stream(self):
        closed = {'value': False}
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            write_file(token_file, '\nsecret1\n')
            transport = _RenewTransport(fail_on_call=2, failure=httpx2.Response(401, stream=_ClosableStream(closed)))
            http = HTTPX2Wrapper(self._file_instance(token_file), {}, transport=transport)

            http.get('https://www.example.com')
            write_file(token_file, '\nsecret2\n')
            http.get('https://www.example.com')

            assert transport.requests[-1].headers['Authorization'] == 'Bearer secret2'
            # The failed first response's stream must be closed before the retry, or the connection leaks.
            assert closed['value'] is True
