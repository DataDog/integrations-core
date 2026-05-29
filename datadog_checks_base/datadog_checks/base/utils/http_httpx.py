# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from datetime import timedelta
from typing import Any

import httpx2 as httpx
from binary import KIBIBYTE

from datadog_checks.base.config import is_affirmative

from .headers import get_default_headers, update_headers
from .http_exceptions import (
    HTTPConnectionError,
    HTTPError,
    HTTPInvalidURLError,
    HTTPRequestError,
    HTTPStatusError,
    HTTPTimeoutError,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
# Matches the effective chunk size used by RequestsWrapper.iter_content (http.py:415 multiplies by KIBIBYTE).
DEFAULT_CHUNK_SIZE = 16 * KIBIBYTE

STANDARD_FIELDS = {
    'allow_redirects': True,
    'connect_timeout': None,
    'extra_headers': None,
    'headers': None,
    'log_requests': False,
    'password': None,
    'read_timeout': None,
    'timeout': DEFAULT_TIMEOUT,
    'tls_ca_cert': None,
    'tls_cert': None,
    'tls_private_key': None,
    'tls_verify': True,
    'username': None,
}

DEFAULT_REMAPPED_FIELDS: dict[str, dict[str, Any]] = {}

REQUEST_KWARGS = frozenset(
    {
        'params',
        'json',
        'data',
        'content',
        'files',
        'cookies',
        'headers',
        'extra_headers',
        'timeout',
        'follow_redirects',
    }
)


def _make_timeout(connect: float, read: float) -> httpx.Timeout:
    return httpx.Timeout(connect=connect, read=read, write=None, pool=None)


def _build_basic_auth(config: dict[str, Any]) -> httpx.BasicAuth | None:
    if config['username'] is not None and config['password'] is not None:
        return httpx.BasicAuth(config['username'], config['password'])
    return None


def _build_verify(config: dict[str, Any]) -> bool | str:
    if isinstance(config['tls_ca_cert'], str):
        return config['tls_ca_cert']
    if not is_affirmative(config['tls_verify']):
        return False
    return True


def _build_cert(config: dict[str, Any]) -> str | tuple[str, str] | None:
    cert = config['tls_cert']
    if not isinstance(cert, str):
        return None
    private_key = config['tls_private_key']
    if isinstance(private_key, str):
        return (cert, private_key)
    return cert


def _build_timeout(config: dict[str, Any]) -> tuple[float, float]:
    base = float(config['timeout'])
    connect = float(config['connect_timeout']) if config['connect_timeout'] is not None else base
    read = float(config['read_timeout']) if config['read_timeout'] is not None else base
    return connect, read


def _map_httpx_exception(exc: httpx.HTTPError | httpx.InvalidURL) -> HTTPError:
    """Translate an httpx2 exception into the library-agnostic equivalent."""
    # ConnectError -> HTTPConnectionError pairs 1:1 with the Step 3a widening (PR #22864).
    # Mid-stream NetworkError/ReadError/WriteError stay HTTPRequestError on purpose.
    if isinstance(exc, httpx.InvalidURL):
        return HTTPInvalidURLError(str(exc) or exc.__class__.__name__, request=getattr(exc, 'request', None))
    if isinstance(exc, httpx.TimeoutException):
        return HTTPTimeoutError(str(exc) or exc.__class__.__name__, request=getattr(exc, 'request', None))
    if isinstance(exc, httpx.ConnectError):
        return HTTPConnectionError(str(exc) or exc.__class__.__name__, request=getattr(exc, 'request', None))
    if isinstance(exc, httpx.HTTPStatusError):
        return HTTPStatusError(
            str(exc) or exc.__class__.__name__,
            request=getattr(exc, 'request', None),
            response=getattr(exc, 'response', None),
        )
    if isinstance(exc, httpx.RequestError):
        return HTTPRequestError(str(exc) or exc.__class__.__name__, request=getattr(exc, 'request', None))
    return HTTPError(str(exc) or exc.__class__.__name__)


class HTTPXResponseAdapter:
    """Wraps an httpx2.Response to satisfy HTTPResponseProtocol."""

    __slots__ = ('_response',)

    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def content(self) -> bytes:
        return self._response.read()

    @property
    def text(self) -> str:
        self._response.read()
        return self._response.text

    @property
    def headers(self) -> Mapping[str, str]:
        return self._response.headers

    @property
    def ok(self) -> bool:
        return self._response.status_code < 400

    @property
    def reason(self) -> str:
        return self._response.reason_phrase

    @property
    def encoding(self) -> str | None:
        return self._response.encoding

    @encoding.setter
    def encoding(self, value: str | None) -> None:
        self._response.encoding = value

    @property
    def url(self) -> str:
        return str(self._response.url)

    @property
    def cookies(self) -> httpx.Cookies:
        return self._response.cookies

    @property
    def elapsed(self) -> timedelta:
        try:
            return self._response.elapsed
        except RuntimeError:
            LOGGER.debug('elapsed unavailable for response from %s', self._response.url)
            return timedelta(0)

    def json(self, **kwargs: Any) -> Any:
        self._response.read()
        return self._response.json(**kwargs)

    def raise_for_status(self) -> None:
        # Mirror requests semantics (4xx/5xx only); httpx2 also raises on 3xx.
        if self._response.status_code < 400:
            return
        try:
            self._response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise _map_httpx_exception(exc) from exc

    def close(self) -> None:
        self._response.close()

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes | str]:
        effective_size = chunk_size if chunk_size is not None else DEFAULT_CHUNK_SIZE
        encoding = self._response.encoding or 'utf-8'
        for chunk in self._response.iter_bytes(chunk_size=effective_size):
            yield chunk.decode(encoding) if decode_unicode else chunk

    def iter_lines(
        self,
        chunk_size: int | None = None,  # noqa: ARG002 - httpx2 buffers lines internally; kept for HTTPResponseProtocol parity
        decode_unicode: bool = False,
        delimiter: bytes | str | None = None,
    ) -> Iterator[bytes | str]:
        if delimiter is not None:
            raise NotImplementedError("HTTPXResponseAdapter.iter_lines does not support custom delimiters")
        encoding = self._response.encoding or 'utf-8'
        for line in self._response.iter_lines():
            yield line if decode_unicode else line.encode(encoding)

    def __enter__(self) -> 'HTTPXResponseAdapter':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None:
        self.close()
        return None


class HTTPXWrapper:
    """Implements HTTPClientProtocol using a single shared httpx2.Client per wrapper."""

    __slots__ = (
        '_client',
        '_log_requests',
        'logger',
        'options',
    )

    def __init__(
        self,
        instance: dict[str, Any],
        init_config: dict[str, Any] | None = None,
        remapper: dict[str, dict[str, Any]] | None = None,
        logger: logging.Logger | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.logger = logger or LOGGER
        init_config = init_config or {}

        config = self._resolve_config(instance, init_config, remapper)

        headers = get_default_headers()
        if config['headers']:
            headers.clear()
            update_headers(headers, config['headers'])
        if config['extra_headers']:
            update_headers(headers, config['extra_headers'])

        auth = _build_basic_auth(config)
        verify = _build_verify(config)
        cert = _build_cert(config)
        timeout = _build_timeout(config)
        allow_redirects = is_affirmative(config['allow_redirects'])

        # proxies=None mirrors RequestsWrapper.options for consumers (e.g. http_check). Wiring is Phase 3.
        self.options: dict[str, Any] = {
            'auth': auth,
            'cert': cert,
            'headers': headers,
            'proxies': None,
            'timeout': timeout,
            'verify': verify,
            'allow_redirects': allow_redirects,
        }

        self._log_requests = is_affirmative(config['log_requests'])
        self._client = self._build_client(transport)

    @staticmethod
    def _resolve_config(
        instance: dict[str, Any],
        init_config: dict[str, Any],
        remapper: dict[str, dict[str, Any]] | None,
    ) -> dict[str, Any]:
        default_fields = dict(STANDARD_FIELDS)
        default_fields['log_requests'] = init_config.get('log_requests', default_fields['log_requests'])
        default_fields['timeout'] = init_config.get('timeout', default_fields['timeout'])

        config = {field: instance.get(field, value) for field, value in default_fields.items()}

        remapper = dict(remapper) if remapper else {}
        remapper.update(DEFAULT_REMAPPED_FIELDS)

        for remapped_field, data in remapper.items():
            field = data.get('name')
            if field not in STANDARD_FIELDS:
                continue
            if field in instance:
                continue

            default = default_fields[field]
            if data.get('invert'):
                default = not default

            value = instance.get(remapped_field, data.get('default', default))
            if data.get('invert'):
                value = not is_affirmative(value)

            config[field] = value
        return config

    def _build_client(self, transport: httpx.BaseTransport | None) -> httpx.Client:
        kwargs: dict[str, Any] = {
            'headers': self.options['headers'],
            'timeout': _make_timeout(self.options['timeout'][0], self.options['timeout'][1]),
            'follow_redirects': self.options['allow_redirects'],
            'verify': self.options['verify'],
        }
        if self.options['cert'] is not None:
            kwargs['cert'] = self.options['cert']
        if self.options['auth'] is not None:
            kwargs['auth'] = self.options['auth']
        if transport is not None:
            kwargs['transport'] = transport
        return httpx.Client(**kwargs)

    def get_header(self, name: str, default: str | None = None) -> str | None:
        for key, value in self.options['headers'].items():
            if key.lower() == name.lower():
                return value
        return default

    def set_header(self, name: str, value: str) -> None:
        # Mirror into both stores: options['headers'] is the public shape, _client.headers is what httpx2 sends.
        for key in list(self.options['headers']):
            if key.lower() == name.lower():
                self.options['headers'][key] = value
                self._client.headers[key] = value
                return
        self.options['headers'][name] = value
        self._client.headers[name] = value

    def get(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request('GET', url, options)

    def post(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request('POST', url, options)

    def put(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request('PUT', url, options)

    def delete(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request('DELETE', url, options)

    def head(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request('HEAD', url, options)

    def patch(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request('PATCH', url, options)

    def options_method(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request('OPTIONS', url, options)

    def _request(self, method: str, url: str, options: dict[str, Any]) -> HTTPXResponseAdapter:
        if self._log_requests:
            self.logger.debug('Sending %s request to %s', method, url)

        request_kwargs = self._build_request_kwargs(options)
        follow_redirects = request_kwargs.pop('follow_redirects', httpx.USE_CLIENT_DEFAULT)
        try:
            request = self._client.build_request(method, url, **request_kwargs)
            response = self._client.send(request, stream=True, follow_redirects=follow_redirects)
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            raise _map_httpx_exception(exc) from exc
        return HTTPXResponseAdapter(response)

    def _build_request_kwargs(self, options: dict[str, Any]) -> dict[str, Any]:
        """Translate call-site options to httpx2.Client.request kwargs."""
        # OM v2 scraper injects stream=True unconditionally (base_scraper.py:459). The wrapper
        # always streams internally, so drop the kwarg silently rather than raising on it.
        options = {k: v for k, v in options.items() if k != 'stream'}

        unknown = set(options) - REQUEST_KWARGS
        if unknown:
            raise TypeError(f"HTTPXWrapper does not support per-request kwargs: {sorted(unknown)}")
        kwargs: dict[str, Any] = {}
        passthrough = ('params', 'json', 'data', 'content', 'files', 'cookies')
        for key in passthrough:
            if key in options:
                kwargs[key] = options[key]

        extra_headers = options.get('extra_headers')
        headers = options.get('headers')
        merged_headers: dict[str, str] | None = None
        if headers is not None or extra_headers is not None:
            merged_headers = {}
            if headers is not None:
                merged_headers.update(headers)
            if extra_headers is not None:
                merged_headers.update(extra_headers)
        if merged_headers is not None:
            kwargs['headers'] = merged_headers

        if 'timeout' in options:
            timeout_value = options['timeout']
            if isinstance(timeout_value, (tuple, list)) and len(timeout_value) == 2:
                kwargs['timeout'] = _make_timeout(float(timeout_value[0]), float(timeout_value[1]))
            else:
                kwargs['timeout'] = float(timeout_value)  # type: ignore[arg-type]

        if 'follow_redirects' in options:
            kwargs['follow_redirects'] = bool(options['follow_redirects'])

        return kwargs

    def close(self) -> None:
        client = getattr(self, '_client', None)
        if client is not None:
            client.close()

    def __enter__(self) -> 'HTTPXWrapper':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None:
        self.close()
        return None

    def __del__(self) -> None:  # no cov
        try:
            self.close()
        except AttributeError:
            pass
