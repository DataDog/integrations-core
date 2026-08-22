# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ast
import pathlib

import mock
import pytest
import requests
from requests.adapters import HTTPAdapter

from datadog_checks.base.utils.http import RequestsWrapper, ResponseWrapper
from datadog_checks.base.utils.http_protocol import HTTPResponse
from datadog_checks.dev.http import MockHTTPResponse

from .common import get_wire_headers

pytestmark = [pytest.mark.unit]


class TestClose:
    def test_close_without_session_is_noop(self):
        http = RequestsWrapper({}, {})
        http.close()
        assert http._session is None

    def test_close_closes_underlying_session(self):
        http = RequestsWrapper({}, {})
        session = http.session
        with mock.patch.object(session, 'close') as close:
            http.close()
        close.assert_called_once_with()

    def test_close_resets_session(self):
        http = RequestsWrapper({}, {})
        first = http.session
        http.close()
        assert http._session is None
        assert http.session is not first

    def test_close_is_idempotent_after_open(self):
        http = RequestsWrapper({}, {})
        assert http.session is not None
        http.close()
        http.close()
        assert http._session is None

    def test_request_succeeds_after_close(self):
        http = RequestsWrapper({}, {})
        http.persist_connections = True
        with mock.patch('requests.Session.get') as get:
            http.get('http://example.com')
            first = http.session
            http.close()
            http.get('http://example.com')
            second = http.session
        assert get.call_count == 2
        assert second is not first


class TestDisableAuth:
    def test_disable_auth_overrides_config_basic_auth(self):
        http = RequestsWrapper({'username': 'user', 'password': 'pass'}, {})
        assert http.options['auth'] == ('user', 'pass')
        http.disable_auth()
        assert http.options['auth'] is not None
        assert http.options['auth'] != ('user', 'pass')

    def test_disable_auth_preserves_trust_env(self):
        http = RequestsWrapper({}, {})
        http.disable_auth()
        assert http.trust_env is True

    def test_netrc_header_injected_without_disable_auth(self):
        http = RequestsWrapper({}, {})
        http.options['auth'] = None
        captured = {}

        def fake_send(session_self, request, **kwargs):
            captured['headers'] = dict(request.headers)
            response = requests.Response()
            response.status_code = 200
            return response

        with (
            mock.patch('requests.sessions.get_netrc_auth', return_value=('netrc-user', 'netrc-pass')),
            mock.patch('requests.sessions.Session.send', new=fake_send),
        ):
            http.get('http://example.com')

        assert 'Authorization' in captured['headers']

    def test_disable_auth_suppresses_netrc_header(self):
        http = RequestsWrapper({}, {})
        captured = {}

        def fake_send(session_self, request, **kwargs):
            captured['headers'] = dict(request.headers)
            response = requests.Response()
            response.status_code = 200
            return response

        with (
            mock.patch('requests.sessions.get_netrc_auth', return_value=('netrc-user', 'netrc-pass')),
            mock.patch('requests.sessions.Session.send', new=fake_send),
        ):
            http.disable_auth()
            http.get('http://example.com')

        assert 'Authorization' not in captured['headers']


class TestCookies:
    def test_get_cookie_missing_returns_default(self):
        http = RequestsWrapper({}, {})
        assert http.get_cookie('missing') is None
        assert http.get_cookie('missing', 'fallback') == 'fallback'

    def test_get_cookie_returns_value(self):
        http = RequestsWrapper({}, {})
        http.session.cookies.set('csrftoken', 'abc123')
        value = http.get_cookie('csrftoken')
        assert value == 'abc123'
        assert isinstance(value, str)

    def test_get_cookie_conflict_returns_default(self):
        http = RequestsWrapper({}, {})
        http.session.cookies.set('dup', 'a', domain='a.example.com')
        http.session.cookies.set('dup', 'b', domain='b.example.com')
        assert http.get_cookie('dup', 'fallback') == 'fallback'

    def test_per_request_cookies_reach_the_request(self):
        http = RequestsWrapper({}, {})

        wire_headers = get_wire_headers(http, cookies={'proxy': 'approved'})

        assert wire_headers['Cookie'] == 'proxy=approved'


class TestTrustEnv:
    def test_trust_env_defaults_to_true(self):
        http = RequestsWrapper({}, {})
        assert http.trust_env is True

    def test_trust_env_propagates_to_existing_session(self):
        http = RequestsWrapper({}, {})
        session = http.session
        http.trust_env = False
        assert http.trust_env is False
        assert session.trust_env is False

    def test_trust_env_applies_to_new_session(self):
        http = RequestsWrapper({}, {})
        http.trust_env = False
        assert http.session.trust_env is False

    def test_trust_env_reset_to_true(self):
        http = RequestsWrapper({}, {})
        http.trust_env = False
        http.trust_env = True
        assert http.session.trust_env is True

    def test_trust_env_adopts_injected_session(self):
        session = requests.Session()
        session.trust_env = False
        http = RequestsWrapper({}, {}, session=session)
        assert http.trust_env is False

    def test_trust_env_defaults_true_when_injected_session_lacks_attribute(self):
        http = RequestsWrapper({}, {}, session=mock.Mock(spec=[]))
        assert http.trust_env is True


class TestShouldBypassProxy:
    def test_no_no_proxy_rules_never_bypasses(self):
        http = RequestsWrapper({}, {})
        assert http.no_proxy_uris is None
        assert http.should_bypass_proxy('http://example.com') is False

    def test_matching_host_bypasses(self):
        http = RequestsWrapper({'proxy': {'http': 'http://p:3128', 'no_proxy': 'example.com'}}, {})
        assert http.should_bypass_proxy('http://example.com/path') is True

    def test_non_matching_host_does_not_bypass(self):
        http = RequestsWrapper({'proxy': {'http': 'http://p:3128', 'no_proxy': 'example.com'}}, {})
        assert http.should_bypass_proxy('http://other.com') is False

    def test_wildcard_bypasses_all(self):
        http = RequestsWrapper({'proxy': {'http': 'http://p:3128', 'no_proxy': '*'}}, {})
        assert http.should_bypass_proxy('http://anything.example') is True


class TestClientProtocolSurface:
    def test_client_capabilities_declared(self):
        from datadog_checks.base.utils.http_protocol import HTTPClient

        for name in ('ignore_tls_warning', 'persist_connections', 'tls_config'):
            assert name in HTTPClient.__annotations__, f'{name} missing from HTTPClient'
        assert callable(HTTPClient.should_bypass_proxy)

    def test_tls_escape_hatch_refuses_to_no_op(self):
        from datadog_checks.base.utils.http_protocol import HTTPClient

        class BackendWithoutTheEscapeHatch(HTTPClient):
            pass

        with pytest.raises(NotImplementedError):
            BackendWithoutTheEscapeHatch().apply_tls_to_requests_session(requests.Session())

    def test_wrapper_satisfies_client_surface(self):
        from datadog_checks.base.utils.http_protocol import HTTPClient

        http = RequestsWrapper({}, {})
        for name in HTTPClient.__annotations__:
            assert hasattr(http, name), f'RequestsWrapper missing attribute {name}'
        for name in vars(HTTPClient):
            if not name.startswith('_'):
                assert hasattr(http, name), f'RequestsWrapper missing member {name}'

    def test_shipped_code_reads_only_declared_client_members(self):
        from datadog_checks.base.utils.http_protocol import HTTPClient

        repo_root = pathlib.Path(__file__).resolve().parents[5]
        assert (repo_root / 'datadog_checks_base').is_dir(), f'unexpected repository layout at {repo_root}'

        declared = set(HTTPClient.__annotations__) | {name for name in vars(HTTPClient) if not name.startswith('_')}
        defines_the_surface = {
            repo_root / 'datadog_checks_base/datadog_checks/base/utils/http.py',
            repo_root / 'datadog_checks_base/datadog_checks/base/utils/http_protocol.py',
        }

        # Remove entries as integrations migrate to the declared surface.
        PENDING_MIGRATION = {
            'avi_vantage/datadog_checks/avi_vantage/check.py',
            'cisco_aci/datadog_checks/cisco_aci/api.py',
            'hpe_aruba_edgeconnect/datadog_checks/hpe_aruba_edgeconnect/client.py',
            'http_check/datadog_checks/http_check/http_check.py',
            'openstack_controller/datadog_checks/openstack_controller/api/api_sdk.py',
        }

        undeclared = []
        for path in sorted(repo_root.glob('*/datadog_checks/**/*.py')):
            if path in defines_the_surface:
                continue
            if path.relative_to(repo_root).as_posix() in PENDING_MIGRATION:
                continue
            try:
                tree = ast.parse(path.read_text(encoding='utf-8'))
            except SyntaxError:
                # Vendored Python 2 and cookiecutter templates do not ship a client.
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Attribute)
                    and node.value.attr in ('http', '_http')
                    and node.attr not in declared
                    and not node.attr.startswith('__')
                ):
                    undeclared.append(f'{path.relative_to(repo_root)}:{node.lineno} reads .{node.attr}')

        assert not undeclared, 'client members read by shipped code but not declared on HTTPClient:\n' + '\n'.join(
            undeclared
        )


class TestResponseProtocolSurface:
    def test_promoted_attributes_declared(self):
        annotations = HTTPResponse.__annotations__
        for name in ('encoding', 'elapsed', 'cookies', 'links', 'url', 'history'):
            assert name in annotations, f'{name} missing from HTTPResponse'

    def test_get_peer_cert_declared(self):
        assert callable(HTTPResponse.get_peer_cert)

    def test_context_manager_closes_underlying_response(self):
        response = requests.Response()
        response.close = mock.Mock()
        wrapper = ResponseWrapper(response, 1024)

        with wrapper as entered:
            assert entered is wrapper

        response.close.assert_called_once_with()


def build_requests_response(content: bytes, headers: dict[str, str] | None = None) -> ResponseWrapper:
    """Build through the requests adapter so headers determine encoding."""
    raw = mock.Mock(spec=['status', 'headers', 'reason', 'version'])
    raw.status, raw.headers, raw.reason, raw.version = 200, headers or {}, 'OK', 11
    response = HTTPAdapter().build_response(requests.Request('GET', 'http://example.com').prepare(), raw)
    response._content = content
    response._content_consumed = True
    return ResponseWrapper(response, 1024)


@pytest.mark.parametrize('backend', ['requests', 'mock'])
@pytest.mark.parametrize(
    ('headers', 'expected'),
    [
        (None, None),
        ({'Content-Type': 'application/octet-stream'}, None),
        ({'Content-Type': 'text/plain'}, 'ISO-8859-1'),
        ({'Content-Type': 'text/plain; charset=latin-1'}, 'latin-1'),
        ({'Content-Type': 'application/json'}, 'utf-8'),
        ({'Content-Type': 'application/openmetrics-text; version=1.0.0'}, 'ISO-8859-1'),
        ({'Content-Type': 'TEXT/PLAIN; CHARSET=UTF-8'}, 'UTF-8'),
    ],
)
def test_encoding_derived_from_content_type(backend, headers, expected):
    if backend == 'requests':
        response = build_requests_response(b'abc', headers)
    else:
        response = MockHTTPResponse(content=b'abc', headers=headers)

    assert response.encoding == expected


@pytest.mark.parametrize('backend', ['requests', 'mock'])
def test_decode_unicode_yields_bytes_when_the_encoding_is_undetermined(backend):
    content = 'a: café\nb: 2'.encode('utf-8')
    if backend == 'requests':
        response = build_requests_response(content)
    else:
        response = MockHTTPResponse(content=content)

    assert response.encoding is None
    assert list(response.iter_lines(decode_unicode=True)) == [b'a: caf\xc3\xa9', b'b: 2']
    assert list(response.iter_content(chunk_size=4, decode_unicode=True)) == [b'a: c', b'af\xc3\xa9', b'\nb: ', b'2']


@pytest.mark.parametrize('backend', ['requests', 'mock'])
@pytest.mark.parametrize(
    ('content', 'delimiter', 'decode_unicode', 'expected', 'element_type'),
    [
        (b'', None, False, [], bytes),
        (b'a\n', None, False, [b'a'], bytes),
        (b'a\n\n', None, False, [b'a', b''], bytes),
        (b'a|', b'||', False, [b'a|'], bytes),
        (b'a||', b'||', False, [b'a', b''], bytes),
        ('café\n\n'.encode('utf-8'), None, True, ['café', ''], str),
        ('café||'.encode('utf-8'), '||', True, ['café', ''], str),
    ],
)
def test_iter_lines_contract(
    backend: str,
    content: bytes,
    delimiter: bytes | str | None,
    decode_unicode: bool,
    expected: list[bytes | str],
    element_type: type[bytes] | type[str],
) -> None:
    if backend == 'requests':
        raw_response = requests.Response()
        raw_response._content = content
        raw_response._content_consumed = True
        response = ResponseWrapper(raw_response, 1024)
    else:
        response = MockHTTPResponse(content=content)

    if decode_unicode:
        response.encoding = 'utf-8'

    actual = list(response.iter_lines(decode_unicode=decode_unicode, delimiter=delimiter))

    assert actual == expected
    assert [type(line) for line in actual] == [element_type] * len(expected)


class TestPeerCert:
    def test_returns_cert_from_connection_socket(self):
        response = mock.Mock()
        response.raw.connection.sock.getpeercert.return_value = b'der-bytes'
        wrapper = ResponseWrapper(response, 1024)
        assert wrapper.get_peer_cert(binary_form=True) == b'der-bytes'
        response.raw.connection.sock.getpeercert.assert_called_once_with(binary_form=True)

    def test_returns_decoded_cert_with_default_binary_form(self):
        response = mock.Mock()
        response.raw.connection.sock.getpeercert.return_value = {'subject': ()}
        wrapper = ResponseWrapper(response, 1024)
        assert wrapper.get_peer_cert() == {'subject': ()}
        response.raw.connection.sock.getpeercert.assert_called_once_with(binary_form=False)

    def test_returns_none_when_socket_absent(self):
        response = mock.Mock()
        response.raw.connection.sock = None
        wrapper = ResponseWrapper(response, 1024)
        assert wrapper.get_peer_cert() is None

    def test_returns_none_for_non_tls_socket(self):
        response = mock.Mock()
        response.raw.connection.sock = object()
        wrapper = ResponseWrapper(response, 1024)
        assert wrapper.get_peer_cert() is None


class TestHistory:
    def test_history_items_are_wrapped(self):
        redirect = mock.Mock()
        redirect.status_code = 301
        final = mock.Mock()
        final.history = [redirect]
        wrapper = ResponseWrapper(final, 1024)
        history = wrapper.history
        assert len(history) == 1
        assert isinstance(history[0], ResponseWrapper)
        assert history[0].status_code == 301

    def test_history_item_translates_raise_for_status(self):
        from datadog_checks.base.utils.http_exceptions import HTTPStatusError

        redirect = mock.Mock()
        redirect.raise_for_status.side_effect = requests.exceptions.HTTPError('boom')
        final = mock.Mock()
        final.history = [redirect]
        wrapper = ResponseWrapper(final, 1024)
        with pytest.raises(HTTPStatusError):
            wrapper.history[0].raise_for_status()

    def test_empty_history(self):
        response = mock.Mock()
        response.history = []
        wrapper = ResponseWrapper(response, 1024)
        assert wrapper.history == []
