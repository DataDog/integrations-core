# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import MagicMock, patch

import httpx
import pytest

from datadog_checks.base.utils.http_exceptions import (
    HTTPConnectionError,
    HTTPRequestError,
    HTTPStatusError,
    HTTPTimeoutError,
)
from datadog_checks.base.utils.http_httpx import HTTPXResponseAdapter, HTTPXWrapper, _build_httpx_client


class TestHTTPXResponseAdapter:
    def test_iter_content_yields_bytes_by_default(self):
        response = MagicMock(spec=httpx.Response)
        response.iter_bytes.return_value = iter([b"chunk1", b"chunk2"])
        adapter = HTTPXResponseAdapter(response)

        assert list(adapter.iter_content()) == [b"chunk1", b"chunk2"]

    def test_iter_content_yields_str_when_decode_unicode(self):
        response = MagicMock(spec=httpx.Response)
        response.iter_text.return_value = iter(["chunk1", "chunk2"])
        adapter = HTTPXResponseAdapter(response)

        assert list(adapter.iter_content(decode_unicode=True)) == ["chunk1", "chunk2"]

    def test_iter_lines_yields_bytes_by_default(self):
        response = MagicMock(spec=httpx.Response)
        response.iter_lines.return_value = iter(["line1", "line2"])
        adapter = HTTPXResponseAdapter(response)

        assert list(adapter.iter_lines()) == [b"line1", b"line2"]

    def test_iter_lines_yields_str_when_decode_unicode(self):
        response = MagicMock(spec=httpx.Response)
        response.iter_lines.return_value = iter(["line1", "line2"])
        adapter = HTTPXResponseAdapter(response)

        assert list(adapter.iter_lines(decode_unicode=True)) == ["line1", "line2"]

    def test_raise_for_status_translates_http_status_error(self):
        response = MagicMock(spec=httpx.Response)
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=MagicMock()
        )
        adapter = HTTPXResponseAdapter(response)

        with pytest.raises(HTTPStatusError):
            adapter.raise_for_status()

    def test_context_manager_closes_response_on_exit(self):
        response = MagicMock(spec=httpx.Response)
        adapter = HTTPXResponseAdapter(response)

        with adapter:
            pass

        response.close.assert_called_once()

    def test_response_attributes_accessible(self):
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        adapter = HTTPXResponseAdapter(response)

        assert adapter.status_code == 200


class TestHTTPXWrapper:
    def test_successful_request_returns_response_adapter(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.request.return_value = MagicMock(spec=httpx.Response)

        with patch('datadog_checks.base.utils.http_httpx._build_httpx_client', return_value=mock_client):
            wrapper = HTTPXWrapper({}, {})

        result = wrapper.get("http://example.com")

        assert isinstance(result, HTTPXResponseAdapter)

    def test_timeout_raises_http_timeout_error(self):
        mock_client = MagicMock(spec=httpx.Client)
        request = httpx.Request("GET", "http://example.com")
        mock_client.request.side_effect = httpx.TimeoutException("timed out", request=request)

        with patch('datadog_checks.base.utils.http_httpx._build_httpx_client', return_value=mock_client):
            wrapper = HTTPXWrapper({}, {})

        with pytest.raises(HTTPTimeoutError):
            wrapper.get("http://example.com")

    def test_connect_error_raises_http_connection_error(self):
        mock_client = MagicMock(spec=httpx.Client)
        request = httpx.Request("GET", "http://example.com")
        mock_client.request.side_effect = httpx.ConnectError("connection refused", request=request)

        with patch('datadog_checks.base.utils.http_httpx._build_httpx_client', return_value=mock_client):
            wrapper = HTTPXWrapper({}, {})

        with pytest.raises(HTTPConnectionError):
            wrapper.get("http://example.com")

    def test_invalid_url_raises_http_request_error(self):
        client = MagicMock(spec=httpx.Client)
        client.request.side_effect = httpx.InvalidURL("Invalid URL")
        wrapper = HTTPXWrapper(client)

        with pytest.raises(HTTPRequestError):
            wrapper.get("not a url")

    def test_all_http_methods_delegate_to_client(self):
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.request.return_value = MagicMock(spec=httpx.Response)

        with patch('datadog_checks.base.utils.http_httpx._build_httpx_client', return_value=mock_client):
            wrapper = HTTPXWrapper({}, {})

        url = "http://example.com"
        wrapper.get(url)
        wrapper.post(url)
        wrapper.head(url)
        wrapper.put(url)
        wrapper.patch(url)
        wrapper.delete(url)
        wrapper.options_method(url)

        methods = [call.args[0] for call in mock_client.request.call_args_list]
        assert methods == ["GET", "POST", "HEAD", "PUT", "PATCH", "DELETE", "OPTIONS"]


class TestBuildHttpxClient:
    @staticmethod
    def _get_client_kwargs(instance, init_config=None, **kwargs):
        """Capture the kwargs passed to httpx.Client() without constructing a real client.

        Uses mock.patch so the real httpx.Client is not instantiated, allowing tests to
        inspect constructor arguments (e.g. 'verify') that aren't exposed as attributes.
        """
        if init_config is None:
            init_config = {}
        with patch('datadog_checks.base.utils.http_httpx.httpx.Client') as mock_cls:
            mock_cls.return_value = MagicMock()
            _build_httpx_client(instance, init_config, **kwargs)
        return mock_cls.call_args.kwargs

    # --- Auth ---

    def test_basic_auth_sets_client_auth(self):
        client = _build_httpx_client({'username': 'user', 'password': 'pass'}, {})
        assert isinstance(client.auth, httpx.BasicAuth)

    def test_basic_auth_not_set_without_username(self):
        client = _build_httpx_client({}, {})
        assert client.auth is None

    def test_digest_auth(self):
        client = _build_httpx_client({'username': 'u', 'password': 'p', 'auth_type': 'digest'}, {})
        assert isinstance(client.auth, httpx.DigestAuth)

    def test_kerberos_auth_type_builds_kerberos_adapter(self):
        from datadog_checks.base.utils.httpx_auth import KerberosAuth

        client = _build_httpx_client({'auth_type': 'kerberos'}, {})
        assert isinstance(client.auth, KerberosAuth)

    def test_ntlm_auth_type_builds_ntlm_adapter(self):
        from datadog_checks.base.utils.httpx_auth import NTLMAuth

        client = _build_httpx_client({'auth_type': 'ntlm', 'ntlm_domain': 'DOMAIN\\user', 'password': 'pass'}, {})
        assert isinstance(client.auth, NTLMAuth)

    # --- TLS ---

    def test_tls_verify_false(self):
        kwargs = self._get_client_kwargs({'tls_verify': False})
        assert kwargs['verify'] is False

    def test_tls_ca_cert(self):
        # _get_client_kwargs avoids real SSL context loading
        kwargs = self._get_client_kwargs({'tls_ca_cert': '/path/to/ca.pem'})
        assert kwargs['verify'] == '/path/to/ca.pem'

    def test_tls_verify_true_by_default(self):
        kwargs = self._get_client_kwargs({})
        assert kwargs['verify'] is True

    # --- Redirects ---

    def test_follow_redirects_default_true(self):
        client = _build_httpx_client({}, {})
        assert client.follow_redirects is True

    def test_follow_redirects_false(self):
        client = _build_httpx_client({'allow_redirects': False}, {})
        assert client.follow_redirects is False

    # --- Timeouts ---

    def test_timeout_from_instance(self):
        client = _build_httpx_client({'timeout': 30}, {})
        assert client.timeout.read == 30.0
        assert client.timeout.connect == 30.0

    def test_timeout_read_connect_split(self):
        client = _build_httpx_client({'read_timeout': 20, 'connect_timeout': 5}, {})
        assert client.timeout.read == 20.0
        assert client.timeout.connect == 5.0

    def test_timeout_from_init_config(self):
        client = _build_httpx_client({}, {'timeout': 42})
        assert client.timeout.read == 42.0

    # --- Remapper ---

    def test_remapper_applied(self):
        # 'user' should be remapped to 'username' via remapper dict
        remapper = {'user': {'name': 'username'}}
        client = _build_httpx_client({'user': 'alice', 'password': 'secret'}, {}, remapper=remapper)
        assert isinstance(client.auth, httpx.BasicAuth)

    def test_remapper_invert(self):
        # ssl_validation=False with invert=True → tls_verify=True (not disabled)
        remapper = {'ssl_validation': {'name': 'tls_verify', 'default': False, 'invert': True}}
        kwargs_false = self._get_client_kwargs({'ssl_validation': False}, remapper=remapper)
        assert kwargs_false['verify'] is True

        kwargs_true = self._get_client_kwargs({'ssl_validation': True}, remapper=remapper)
        assert kwargs_true['verify'] is False

    # --- Proxies ---

    def test_skip_proxy_disables_trust_env(self):
        client = _build_httpx_client({'skip_proxy': True}, {})
        assert client.trust_env is False

    def test_proxy_config_converted_to_mounts(self):
        proxy_url = 'http://proxy.example.com:8080'
        kwargs = self._get_client_kwargs({'proxy': {'http': proxy_url}})
        mounts = kwargs.get('mounts') or {}
        assert 'http://' in mounts

    # --- Headers ---

    def test_headers_replaced_when_headers_set(self):
        # When 'headers' is set, it replaces our default Datadog headers;
        # the custom header must be present.
        client = _build_httpx_client({'headers': {'X-Custom': 'value'}}, {})
        assert client.headers.get('x-custom') == 'value'

    def test_extra_headers_merged(self):
        # 'extra_headers' are merged on top of defaults; Datadog User-Agent still present
        client = _build_httpx_client({'extra_headers': {'X-Extra': 'yes'}}, {})
        assert client.headers.get('x-extra') == 'yes'
        assert 'user-agent' in client.headers
