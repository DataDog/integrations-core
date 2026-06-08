# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from datetime import timedelta
from typing import Any, Self

import httpx2
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
REQUEST_KWARGS_SPECIAL = frozenset({'headers', 'extra_headers', 'timeout', 'follow_redirects'})
REQUEST_KWARGS_PASSTHROUGH = REQUEST_KWARGS - REQUEST_KWARGS_SPECIAL
assert REQUEST_KWARGS_PASSTHROUGH | REQUEST_KWARGS_SPECIAL == REQUEST_KWARGS
assert REQUEST_KWARGS_PASSTHROUGH & REQUEST_KWARGS_SPECIAL == frozenset()

UNKNOWN_KWARG_HINTS: dict[str, str] = {
    'verify': "configure 'tls_verify' in instance config, or drop the per-call kwarg",
    'persist': 'drop the kwarg, httpx2 pools connections by default',
    'cert': "configure 'tls_cert' and 'tls_private_key' in instance config",
    'proxies': 'proxy support is not yet wired through to httpx2, see TODO in httpx2.py',
}


def _make_timeout(connect: float, read: float) -> httpx2.Timeout:
    # Pass the read timeout to every phase so write and pool aren't left unbounded.
    return httpx2.Timeout(connect=connect, read=read, write=read, pool=read)


def _build_basic_auth(config: dict[str, Any]) -> httpx2.BasicAuth | None:
    if config['username'] is not None and config['password'] is not None:
        return httpx2.BasicAuth(config['username'], config['password'])
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


def _map_httpx2_exception(exc: httpx2.HTTPError | httpx2.InvalidURL) -> HTTPError:
    """Translate an httpx2 exception into the library-agnostic equivalent."""
    if isinstance(exc, httpx2.InvalidURL):
        return HTTPInvalidURLError(str(exc) or exc.__class__.__name__, request=getattr(exc, 'request', None))
    if isinstance(exc, httpx2.TimeoutException):
        return HTTPTimeoutError(str(exc) or exc.__class__.__name__, request=getattr(exc, 'request', None))
    if isinstance(exc, httpx2.NetworkError):
        return HTTPConnectionError(str(exc) or exc.__class__.__name__, request=getattr(exc, 'request', None))
    if isinstance(exc, httpx2.HTTPStatusError):
        return HTTPStatusError(
            str(exc) or exc.__class__.__name__,
            request=getattr(exc, 'request', None),
            response=getattr(exc, 'response', None),
        )
    if isinstance(exc, httpx2.RequestError):
        return HTTPRequestError(str(exc) or exc.__class__.__name__, request=getattr(exc, 'request', None))
    return HTTPError(str(exc) or exc.__class__.__name__)


class HTTPX2ResponseAdapter:
    """Wraps an httpx2.Response to satisfy HTTPResponseProtocol."""

    __slots__ = ('_response',)

    def __init__(self, response: httpx2.Response) -> None:
        self._response = response

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def content(self) -> bytes:
        try:
            return self._response.read()
        except (httpx2.HTTPError, httpx2.InvalidURL) as exc:
            raise _map_httpx2_exception(exc) from exc

    @property
    def text(self) -> str:
        try:
            self._response.read()
            return self._response.text
        except (httpx2.HTTPError, httpx2.InvalidURL) as exc:
            raise _map_httpx2_exception(exc) from exc

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
        # Encoding is consulted at decode time, not when set. Bytes already read by
        # iter_text or iter_lines stay decoded under the previous encoding.
        self._response.encoding = value

    @property
    def url(self) -> str:
        return str(self._response.url)

    @property
    def cookies(self) -> Mapping[str, str]:
        # Narrowed to Mapping to keep httpx2 out of the wrapper surface. Callers needing
        # the richer httpx2.Cookies API can reach self._response.cookies directly.
        return self._response.cookies

    @property
    def elapsed(self) -> timedelta:
        try:
            return self._response.elapsed
        except RuntimeError:
            LOGGER.debug('elapsed unavailable for response from %s', self._response.url)
            return timedelta(0)

    def json(self, **kwargs: Any) -> Any:
        try:
            self._response.read()
            return self._response.json(**kwargs)
        except (httpx2.HTTPError, httpx2.InvalidURL) as exc:
            raise _map_httpx2_exception(exc) from exc

    def raise_for_status(self) -> None:
        # Mirror requests semantics (4xx/5xx only); httpx2 also raises on 3xx.
        if self._response.status_code < 400:
            return
        try:
            self._response.raise_for_status()
        except httpx2.HTTPStatusError as exc:
            raise _map_httpx2_exception(exc) from exc

    def close(self) -> None:
        self._response.close()

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes | str]:
        effective_size = chunk_size if chunk_size is not None else DEFAULT_CHUNK_SIZE
        try:
            if decode_unicode:
                # iter_text uses an incremental decoder. Manual chunk decoding breaks on
                # multibyte chars split across boundaries.
                yield from self._response.iter_text(chunk_size=effective_size)
                return
            yield from self._response.iter_bytes(chunk_size=effective_size)
        except (httpx2.HTTPError, httpx2.InvalidURL) as exc:
            raise _map_httpx2_exception(exc) from exc

    def iter_lines(
        self,
        chunk_size: int | None = None,  # noqa: ARG002 - httpx2 buffers lines internally. Kept for HTTPResponseProtocol parity
        decode_unicode: bool = False,
        delimiter: bytes | str | None = None,
    ) -> Iterator[bytes | str]:
        if delimiter is not None:
            raise NotImplementedError("HTTPX2ResponseAdapter.iter_lines does not support custom delimiters")
        try:
            if decode_unicode:
                yield from self._response.iter_lines()
                return
            buf = bytearray()
            for chunk in self._response.iter_bytes():
                buf.extend(chunk)
                while (idx := buf.find(b'\n')) != -1:
                    yield bytes(buf[:idx]).rstrip(b'\r')
                    del buf[: idx + 1]
            if buf:
                yield bytes(buf).rstrip(b'\r')
        except (httpx2.HTTPError, httpx2.InvalidURL) as exc:
            raise _map_httpx2_exception(exc) from exc

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None:
        self.close()
        return None


class HTTPX2Wrapper:
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
        transport: httpx2.BaseTransport | None = None,
    ) -> None:
        self.logger = logger or LOGGER
        init_config = init_config or {}

        config = self._resolve_config(instance, init_config, remapper)

        # options['headers'] is a plain dict for parity with RequestsWrapper (http.py:319).
        # Case-folding is applied at request time via httpx2.Headers in _build_request_kwargs;
        # get_header/set_header below do case-insensitive iteration over this dict.
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

        # proxies=None mirrors RequestsWrapper.options for consumers (e.g. http_check).
        # TODO: wire proxies through to httpx2 as part of the ongoing httpx migration.
        # options['headers'] is the per-request source of truth and is re-read in _build_request_kwargs,
        # so direct mutation (__setitem__, update(), whole-dict replacement) reaches the wire.
        # set_header keeps options['headers'] and _client.headers in sync for callers that prefer it.
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

    def _build_client(self, transport: httpx2.BaseTransport | None) -> httpx2.Client:
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
        return httpx2.Client(**kwargs)

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

    def get(self, url: str, **options: Any) -> HTTPX2ResponseAdapter:
        return self._request('GET', url, options)

    def post(self, url: str, **options: Any) -> HTTPX2ResponseAdapter:
        return self._request('POST', url, options)

    def put(self, url: str, **options: Any) -> HTTPX2ResponseAdapter:
        return self._request('PUT', url, options)

    def delete(self, url: str, **options: Any) -> HTTPX2ResponseAdapter:
        return self._request('DELETE', url, options)

    def head(self, url: str, **options: Any) -> HTTPX2ResponseAdapter:
        return self._request('HEAD', url, options)

    def patch(self, url: str, **options: Any) -> HTTPX2ResponseAdapter:
        return self._request('PATCH', url, options)

    def options_method(self, url: str, **options: Any) -> HTTPX2ResponseAdapter:
        return self._request('OPTIONS', url, options)

    def _request(self, method: str, url: str, options: dict[str, Any]) -> HTTPX2ResponseAdapter:
        # stream=True keeps the connection open until the body is consumed (.content/.text/.iter_*)
        # or close() is called. Callers should use it as a context manager when not reading the body.
        if self._log_requests:
            self.logger.debug('Sending %s request to %s', method, url)

        follow_redirects = (
            bool(options['follow_redirects']) if 'follow_redirects' in options else httpx2.USE_CLIENT_DEFAULT
        )
        request_kwargs = self._build_request_kwargs(options, method=method, url=url)
        try:
            request = self._client.build_request(method, url, **request_kwargs)
            response = self._client.send(request, stream=True, follow_redirects=follow_redirects)
        except (httpx2.HTTPError, httpx2.InvalidURL) as exc:
            raise _map_httpx2_exception(exc) from exc
        try:
            return HTTPX2ResponseAdapter(response)
        except BaseException:
            # Close the open stream if anything between send(stream=True) and the wrap raises.
            response.close()
            raise

    def _build_request_kwargs(self, options: dict[str, Any], *, method: str = '', url: str = '') -> dict[str, Any]:
        """Translate call-site options to httpx2.Client.request kwargs."""
        # Drop stream silently because OM v2 scraper passes it unconditionally (base_scraper.py:459).
        # The wrapper streams internally, so the kwarg is meaningless.
        if 'stream' in options:
            self.logger.debug('HTTPX2Wrapper dropping unsupported per-request kwarg: stream')
        options = {k: v for k, v in options.items() if k != 'stream'}

        unknown = set(options) - REQUEST_KWARGS
        if unknown:
            context = f' for {method} {url}' if method or url else ''
            sorted_unknown = sorted(unknown)
            hints = [f'  {k}: {UNKNOWN_KWARG_HINTS[k]}' for k in sorted_unknown if k in UNKNOWN_KWARG_HINTS]
            hint_block = ('\n' + '\n'.join(hints)) if hints else ''
            raise TypeError(f"HTTPX2Wrapper does not support per-request kwargs{context}: {sorted_unknown}{hint_block}")
        kwargs: dict[str, Any] = {}
        for key in REQUEST_KWARGS_PASSTHROUGH:
            if key in options:
                kwargs[key] = options[key]

        # Re-read self.options['headers'] per request so post-init mutations (__setitem__, update(),
        # whole-dict replacement) reach the wire, mirroring RequestsWrapper's ChainMap pattern at http.py:497.
        # Layered order: self.options['headers'] < per-call headers < per-call extra_headers.
        # httpx2.Headers folds keys case-insensitively, matching RequestsWrapper's CaseInsensitiveDict.
        merged = httpx2.Headers(self.options.get('headers') or {})
        headers = options.get('headers')
        if headers:
            merged.update(headers)
        extra_headers = options.get('extra_headers')
        if extra_headers:
            merged.update(extra_headers)
        kwargs['headers'] = merged

        if 'timeout' in options:
            timeout_value = options['timeout']
            if timeout_value is None:
                kwargs['timeout'] = None
            elif isinstance(timeout_value, (tuple, list)) and len(timeout_value) == 2:
                kwargs['timeout'] = _make_timeout(float(timeout_value[0]), float(timeout_value[1]))
            else:
                value = float(timeout_value)
                kwargs['timeout'] = _make_timeout(value, value)

        return kwargs

    def close(self) -> None:
        client = getattr(self, '_client', None)
        if client is not None:
            client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None:
        self.close()
        return None

    def __del__(self) -> None:  # no cov
        try:
            self.close()
        except Exception as exc:
            # Don't propagate from __del__ (interpreter handles it). Log at debug so the swallow is observable.
            self.logger.debug('HTTPX2Wrapper.close raised during __del__: %r', exc)
