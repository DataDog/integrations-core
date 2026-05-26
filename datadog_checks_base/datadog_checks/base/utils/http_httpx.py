# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import timedelta
from typing import Any, Iterator

import httpx

from datadog_checks.base.config import is_affirmative

from .headers import get_default_headers, update_headers
from .http_exceptions import (
    HTTPConnectionError,
    HTTPError,
    HTTPRequestError,
    HTTPStatusError,
    HTTPTimeoutError,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10

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


def _map_httpx_exception(exc: BaseException) -> HTTPError:
    """Translate an httpx exception into the library-agnostic equivalent."""
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
    """Wraps an httpx.Response to satisfy HTTPResponseProtocol."""

    __slots__ = ('_response',)

    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def content(self) -> bytes:
        return self._response.content

    @property
    def text(self) -> str:
        return self._response.text

    @property
    def headers(self) -> Mapping[str, str]:
        return self._response.headers

    @property
    def ok(self) -> bool:
        return self._response.status_code < 400

    @property
    def reason(self) -> str:
        reason = getattr(self._response, 'reason_phrase', None)
        if reason is not None:
            return reason
        return getattr(self._response, 'reason', '') or ''

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
            return timedelta(0)

    def json(self, **kwargs: Any) -> Any:
        return self._response.json(**kwargs)

    def raise_for_status(self) -> None:
        # Mirror requests semantics (4xx/5xx only); httpx also raises on 3xx.
        if self._response.status_code < 400:
            return
        try:
            self._response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise _map_httpx_exception(exc) from exc

    def close(self) -> None:
        self._response.close()

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes | str]:
        content = self._response.content
        if chunk_size is None:
            yield content.decode('utf-8') if decode_unicode else content
            return
        for i in range(0, len(content), max(chunk_size, 1)):
            chunk = content[i : i + chunk_size]
            yield chunk.decode('utf-8') if decode_unicode else chunk

    def iter_lines(
        self,
        chunk_size: int | None = None,
        decode_unicode: bool = False,
        delimiter: bytes | str | None = None,
    ) -> Iterator[bytes | str]:
        if isinstance(delimiter, str):
            delimiter = delimiter.encode('utf-8')
        sep = delimiter or b'\n'
        content = self._response.content
        lines = content.split(sep)
        if lines and not lines[-1]:
            lines.pop()
        for line in lines:
            yield line.decode('utf-8') if decode_unicode else line

    def __enter__(self) -> 'HTTPXResponseAdapter':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None:
        self.close()
        return None


class HTTPXWrapper:
    """Implements HTTPClientProtocol using a single shared httpx.Client per wrapper."""

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

        # `proxies` is None for shape-parity with RequestsWrapper.options; proxy wiring is Phase 3.
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
            'timeout': httpx.Timeout(
                connect=self.options['timeout'][0], read=self.options['timeout'][1], write=None, pool=None
            ),
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
        try:
            response = self._client.request(method, url, **request_kwargs)
        except httpx.HTTPError as exc:
            raise _map_httpx_exception(exc) from exc
        return HTTPXResponseAdapter(response)

    def _build_request_kwargs(self, options: dict[str, Any]) -> dict[str, Any]:
        """Translate call-site options to httpx.Client.request kwargs; unknown kwargs are dropped."""
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
                kwargs['timeout'] = httpx.Timeout(
                    connect=float(timeout_value[0]),
                    read=float(timeout_value[1]),
                    write=None,
                    pool=None,
                )
            else:
                kwargs['timeout'] = float(timeout_value)  # type: ignore[arg-type]

        if 'follow_redirects' in options:
            kwargs['follow_redirects'] = bool(options['follow_redirects'])
        elif 'allow_redirects' in options:
            kwargs['follow_redirects'] = bool(options['allow_redirects'])

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

    def __del__(self) -> None:
        # AttributeError fires when __init__ raised before _client was assigned.
        try:
            self.close()
        except AttributeError:
            pass
