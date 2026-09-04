# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import ssl
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import timedelta
from functools import cache
from typing import TYPE_CHECKING, Any, cast

import requests
from requests import exceptions as requests_exceptions
from urllib3.exceptions import ReadTimeoutError as Urllib3ReadTimeoutError

if TYPE_CHECKING:
    from requests.adapters import _HostParams, _PoolKwargs

from datadog_checks.base.utils import _http_utils

from .http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientConnectTimeoutError,
    HTTPClientError,
    HTTPClientInvalidURLError,
    HTTPClientReadTimeoutError,
    HTTPClientRequestError,
    HTTPClientSSLError,
    HTTPClientStatusError,
    HTTPClientTimeoutError,
)
from .http_protocol import HTTPRequestSnapshot, HTTPResponse
from .tls import create_ssl_context


def _translate_requests_request(
    request: requests.Request | requests.PreparedRequest | None,
) -> HTTPRequestSnapshot | None:
    if request is None:
        return None

    return HTTPRequestSnapshot(
        method=request.method,
        url=request.url,
        headers=request.headers or {},
    )


@cache
def _backend_compat_type[T: BaseException](agnostic: type[T], *backend: type[BaseException]) -> type[T]:
    """Add requests bases so released checks' exception handlers keep matching."""
    bases = tuple(dict.fromkeys((agnostic, *backend)))
    most_derived_bases = tuple(
        base for base in bases if not any(base is not candidate and issubclass(candidate, base) for candidate in bases)
    )
    compat = type(agnostic.__name__, most_derived_bases, {})
    compat.__module__ = agnostic.__module__
    compat.__qualname__ = agnostic.__qualname__
    compat.__doc__ = agnostic.__doc__
    return compat


# Requests must be first so its initializer populates request, response, and simplejson fields.
_COMPAT_JSON_DECODE_ERROR = _backend_compat_type(requests_exceptions.JSONDecodeError, json.JSONDecodeError)


def _translate_json_decode_error(exc: requests_exceptions.JSONDecodeError) -> json.JSONDecodeError:
    if isinstance(exc, _COMPAT_JSON_DECODE_ERROR):
        return cast(json.JSONDecodeError, exc)

    args: list[Any] = [exc.msg, exc.doc, exc.pos]
    if (end := getattr(exc, 'end', None)) is not None:
        args.append(end)
    return cast(
        json.JSONDecodeError,
        _COMPAT_JSON_DECODE_ERROR(
            *args,
            request=getattr(exc, 'request', None),
            response=getattr(exc, 'response', None),
        ),
    )


def _translated_http_error[T: HTTPClientError](
    agnostic: type[T],
    exc: requests_exceptions.RequestException,
    *,
    response: HTTPResponse | None = None,
) -> T:
    backend_response = getattr(exc, 'response', None)
    if response is None and backend_response is not None:
        response = RequestsResponseAdapter(backend_response)

    # Exception classes are hashable; mypy applies the instances' hashability to the cached generic.
    error_type = _backend_compat_type(agnostic, type(exc))  # type: ignore[arg-type]
    return error_type(
        str(exc) or type(exc).__name__,
        request=_translate_requests_request(getattr(exc, 'request', None)),
        response=response,
    )


def _translate_requests_exception(
    exc: BaseException, *, response: HTTPResponse | None = None
) -> HTTPClientError | json.JSONDecodeError:
    """Map a requests exception to its agnostic compatibility type, most-specific first."""
    if isinstance(exc, HTTPClientError):
        return exc
    if isinstance(exc, requests_exceptions.JSONDecodeError):
        return _translate_json_decode_error(exc)
    if isinstance(
        exc,
        (
            requests_exceptions.InvalidURL,
            requests_exceptions.MissingSchema,
            requests_exceptions.InvalidSchema,
            requests_exceptions.URLRequired,
        ),
    ):
        return _translated_http_error(HTTPClientInvalidURLError, exc, response=response)
    if isinstance(exc, requests_exceptions.SSLError):
        return _translated_http_error(HTTPClientSSLError, exc, response=response)
    if isinstance(exc, requests_exceptions.ConnectTimeout):
        return _translated_http_error(HTTPClientConnectTimeoutError, exc, response=response)
    if isinstance(exc, requests_exceptions.ReadTimeout):
        return _translated_http_error(HTTPClientReadTimeoutError, exc, response=response)
    if isinstance(exc, requests_exceptions.Timeout):
        return _translated_http_error(HTTPClientTimeoutError, exc, response=response)
    if isinstance(exc, requests_exceptions.ConnectionError) and any(
        isinstance(cause, Urllib3ReadTimeoutError) for cause in (exc.__context__, exc.args[0] if exc.args else None)
    ):
        return _translated_http_error(HTTPClientReadTimeoutError, exc, response=response)
    if isinstance(exc, requests_exceptions.ConnectionError):
        return _translated_http_error(HTTPClientConnectionError, exc, response=response)
    if isinstance(exc, requests_exceptions.InvalidHeader):
        return _translated_http_error(HTTPClientRequestError, exc, response=response)
    if isinstance(exc, requests_exceptions.ContentDecodingError):
        return _translated_http_error(HTTPClientRequestError, exc, response=response)
    if isinstance(exc, requests_exceptions.HTTPError):
        return _translated_http_error(HTTPClientStatusError, exc, response=response)
    if isinstance(exc, requests_exceptions.RequestException):
        return _translated_http_error(HTTPClientRequestError, exc, response=response)
    return HTTPClientError(str(exc) or type(exc).__name__)


@contextmanager
def translate_http_errors() -> Iterator[None]:
    """Re-raise requests exceptions as their backend-neutral equivalents."""
    try:
        yield
    except requests_exceptions.RequestException as exc:
        translated = _translate_requests_exception(exc)
        # Compatibility types retain a requests base, so an outer translation seam catches them too.
        if translated is exc:
            raise
        raise translated from exc


class RequestsResponseAdapter:
    """Expose a requests response through the backend-neutral response contract."""

    __slots__ = ('_default_chunk_size', '_response')

    def __init__(self, response: requests.Response, default_chunk_size: int | None = None) -> None:
        self._response = response
        self._default_chunk_size = default_chunk_size

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def content(self) -> bytes:
        with translate_http_errors():
            return self._response.content

    @property
    def text(self) -> str:
        with translate_http_errors():
            return self._response.text

    @property
    def headers(self) -> Mapping[str, str]:
        return self._response.headers

    @property
    def encoding(self) -> str | None:
        return self._response.encoding

    @encoding.setter
    def encoding(self, value: str | None) -> None:
        self._response.encoding = value

    @property
    def elapsed(self) -> timedelta:
        return self._response.elapsed

    @property
    def cookies(self) -> Mapping[str, str]:
        return self._response.cookies

    @property
    def links(self) -> Mapping[str, Mapping[str, str]]:
        return self._response.links

    @property
    def url(self) -> str:
        return self._response.url

    @property
    def history(self) -> list[RequestsResponseAdapter]:
        return [RequestsResponseAdapter(response, self._default_chunk_size) for response in self._response.history]

    @property
    def ok(self) -> bool:
        return self._response.ok

    @property
    def reason(self) -> str:
        return self._response.reason

    def json(self, **kwargs: Any) -> Any:
        with translate_http_errors():
            return self._response.json(**kwargs)

    def raise_for_status(self) -> None:
        try:
            self._response.raise_for_status()
        except requests_exceptions.HTTPError as exc:
            raise _translate_requests_exception(exc, response=self) from exc

    def close(self) -> None:
        self._response.close()

    def get_peer_cert(self, binary_form: bool = False) -> bytes | dict | None:
        raw = getattr(self._response, 'raw', None)
        connection = getattr(raw, 'connection', None)
        sock = getattr(connection, 'sock', None)
        getpeercert = getattr(sock, 'getpeercert', None)
        if getpeercert is None:
            return None
        return getpeercert(binary_form=binary_form)

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes | str]:
        if chunk_size is None:
            chunk_size = self._default_chunk_size

        with translate_http_errors():
            yield from self._response.iter_content(chunk_size=chunk_size, decode_unicode=decode_unicode)

    def iter_lines(
        self,
        chunk_size: int | None = None,
        decode_unicode: bool = False,
        delimiter: bytes | str | None = None,
    ) -> Iterator[bytes | str]:
        if chunk_size is None:
            chunk_size = self._default_chunk_size

        with translate_http_errors():
            yield from self._response.iter_lines(
                chunk_size=chunk_size, decode_unicode=decode_unicode, delimiter=delimiter
            )

    def __enter__(self) -> RequestsResponseAdapter:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __iter__(self) -> Iterator[bytes | str]:
        return self.iter_content(128)

    def __bool__(self) -> bool:
        return bool(self._response)

    def __repr__(self) -> str:
        return repr(self._response)

    def __str__(self) -> str:
        return str(self._response)


class SSLContextAdapter(requests.adapters.HTTPAdapter):
    """Use an integration-managed SSL context for requests connections."""

    def __init__(self, ssl_context: ssl.SSLContext, **kwargs: Any) -> None:
        self.ssl_context = ssl_context
        super().__init__()

    def init_poolmanager(self, connections: int, maxsize: int, block: bool = False, **pool_kwargs: Any) -> None:
        pool_kwargs['ssl_context'] = self.ssl_context
        return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

    def cert_verify(self, conn: Any, url: str, verify: bool | str, cert: Any) -> None:
        """Keep certificate verification in the integration-managed SSL context."""
        pass

    def build_connection_pool_key_attributes(
        self,
        request: requests.PreparedRequest,
        verify: bool | str,
        cert: Any = None,
    ) -> tuple[_HostParams, _PoolKwargs]:
        """Include the managed SSL context in requests' connection-pool key."""
        host_params, _ = super().build_connection_pool_key_attributes(request, verify, cert)
        pool_kwargs = cast('_PoolKwargs', {'ssl_context': self.ssl_context})
        return host_params, pool_kwargs


def create_https_adapter(
    tls_config: Mapping[str, Any], *, use_host_header: bool = False
) -> requests.adapters.HTTPAdapter:
    """Create a requests adapter for the supplied TLS behavior."""
    context = create_ssl_context(tls_config)
    if use_host_header:

        class SSLContextHostHeaderAdapter(SSLContextAdapter, _http_utils.HostHeaderSSLAdapter):
            def __init__(self, ssl_context: ssl.SSLContext, **kwargs: Any) -> None:
                SSLContextAdapter.__init__(self, ssl_context, **kwargs)
                _http_utils.HostHeaderSSLAdapter.__init__(self, **kwargs)

            def init_poolmanager(self, connections: int, maxsize: int, block: bool = False, **pool_kwargs: Any) -> None:
                pool_kwargs['ssl_context'] = self.ssl_context
                return _http_utils.HostHeaderSSLAdapter.init_poolmanager(
                    self, connections, maxsize, block=block, **pool_kwargs
                )

        return SSLContextHostHeaderAdapter(context)

    return SSLContextAdapter(context)


if TYPE_CHECKING:
    response: HTTPResponse = RequestsResponseAdapter(requests.Response())
