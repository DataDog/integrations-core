# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import ipaddress
import logging
import os
import re
from collections.abc import Iterator, Mapping
from copy import deepcopy
from datetime import timedelta
from typing import Any, Self
from urllib.parse import urlparse
from urllib.request import getproxies

import httpx2
from binary import KIBIBYTE

# Private httpx2 API (pinned httpx2==2.2.0). _env_proxies hard-codes its return shape, so re-verify on any bump.
from httpx2._utils import get_environment_proxies

from datadog_checks.base.agent import datadog_agent
from datadog_checks.base.config import is_affirmative
from datadog_checks.base.errors import ConfigurationError

from .common import ensure_unicode
from .headers import get_default_headers, update_headers
from .http_exceptions import (
    HTTPConnectionError,
    HTTPError,
    HTTPInvalidURLError,
    HTTPRequestError,
    HTTPStatusError,
    HTTPTimeoutError,
)
from .time import get_timestamp

LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
# Matches the effective chunk size used by RequestsWrapper.iter_content (http.py:415 multiplies by KIBIBYTE).
DEFAULT_CHUNK_SIZE = 16 * KIBIBYTE

# Fallback token lifetime (seconds) when an OAuth response omits a usable expires_in, mirroring http.py:66.
DEFAULT_EXPIRATION = 300

# options['proxies'] sentinel stored when skip_proxy is set, for parity with RequestsWrapper.
# trust_env=False is what actually keeps httpx2 from reading HTTP_PROXY/HTTPS_PROXY.
PROXY_SETTINGS_DISABLED = {'http': '', 'https': ''}

STANDARD_FIELDS = {
    'allow_redirects': True,
    'auth_token': None,
    'connect_timeout': None,
    'extra_headers': None,
    'headers': None,
    'log_requests': False,
    'password': None,
    'proxy': None,
    'read_timeout': None,
    'skip_proxy': False,
    'timeout': DEFAULT_TIMEOUT,
    'tls_ca_cert': None,
    'tls_cert': None,
    'tls_private_key': None,
    'tls_verify': True,
    'username': None,
}

# Known legacy field aliases, mirrored from RequestsWrapper (http.py:103-107) for parity.
DEFAULT_REMAPPED_FIELDS = {
    # Forward-parity placeholder: inert until kerberos_auth is added to STANDARD_FIELDS.
    'kerberos': {'name': 'kerberos_auth'},
    # TODO: Remove in 6.13
    'no_proxy': {'name': 'skip_proxy'},
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
        'auth',
    }
)
REQUEST_KWARGS_SPECIAL = frozenset({'headers', 'extra_headers', 'timeout', 'follow_redirects', 'auth'})
REQUEST_KWARGS_PASSTHROUGH = REQUEST_KWARGS - REQUEST_KWARGS_SPECIAL
assert REQUEST_KWARGS_PASSTHROUGH | REQUEST_KWARGS_SPECIAL == REQUEST_KWARGS
assert REQUEST_KWARGS_PASSTHROUGH & REQUEST_KWARGS_SPECIAL == frozenset()

UNKNOWN_KWARG_HINTS: dict[str, str] = {
    'allow_redirects': "use 'follow_redirects' instead (httpx2 name for this kwarg)",
    'verify': "configure 'tls_verify' in instance config, or drop the per-call kwarg",
    'persist': 'drop the kwarg, httpx2 pools connections by default',
    'cert': "configure 'tls_cert' and 'tls_private_key' in instance config",
    'proxies': "configure 'proxy' in instance config; per-request proxy support is unavailable",
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
    return (
        os.environ.get('REQUESTS_CA_BUNDLE')
        or os.environ.get('CURL_CA_BUNDLE')
        or os.environ.get('SSL_CERT_FILE')
        or os.environ.get('SSL_CERT_DIR')
        or True
    )


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
    # httpx2 has no dedicated SSL/cert exception: TLS failures surface as ConnectError (a NetworkError),
    # so they fold into the generic HTTPConnectionError. The HTTPSSLError subtype is intentionally unproduced here.
    if isinstance(exc, httpx2.NetworkError):
        return HTTPConnectionError(str(exc) or exc.__class__.__name__, request=getattr(exc, 'request', None))
    if isinstance(exc, httpx2.HTTPStatusError):
        # response is attached at the raise_for_status seam (the agnostic adapter), never the raw one here
        return HTTPStatusError(
            str(exc) or exc.__class__.__name__,
            request=getattr(exc, 'request', None),
        )
    if isinstance(exc, httpx2.RequestError):
        return HTTPRequestError(str(exc) or exc.__class__.__name__, request=getattr(exc, 'request', None))
    return HTTPError(str(exc) or exc.__class__.__name__)


def should_bypass_proxy(url: str, no_proxy_uris: list[str]) -> bool:
    # Copied from RequestsWrapper (http.py) so no_proxy matching stays identical after the httpx migration.
    # Accepts a URL and a list of no_proxy URIs
    # Returns True if URL should bypass the proxy.
    parsed_uri_parts = urlparse(url)
    parsed_uri = parsed_uri_parts.hostname

    if '*' in no_proxy_uris:
        # A single * character is supported, which matches all hosts, and effectively disables the proxy.
        # See: https://curl.haxx.se/libcurl/c/CURLOPT_NOPROXY.html
        return True

    if parsed_uri_parts.scheme == "unix":
        # Unix domain sockets semantically do not make sense to proxy
        return True

    for no_proxy_uri in no_proxy_uris:
        try:
            # If no_proxy_uri is an IP or IP CIDR.
            # A ValueError is raised if address does not represent a valid IPv4 or IPv6 address.
            ip_network = ipaddress.ip_network(ensure_unicode(no_proxy_uri))
            ip_address = ipaddress.ip_address(ensure_unicode(parsed_uri))
            if ip_address in ip_network:
                return True
        except ValueError:
            # Treat no_proxy_uri as a domain name
            # A domain name matches that name and all subdomains.
            #   e.g. "foo.com" matches "foo.com" and "bar.foo.com"
            # A domain name with a leading "." matches subdomains only.
            #   e.g. ".y.com" matches "x.y.com" but not "y.com".
            if no_proxy_uri.startswith((".", "*.")):
                # Support wildcard subdomain; treat as leading dot "."
                # e.g. "*.example.domain" as ".example.domain"
                dot_no_proxy_uri = no_proxy_uri.lstrip("*")
            else:
                # Used for matching subdomains.
                dot_no_proxy_uri = ".{}".format(no_proxy_uri)
            if no_proxy_uri == parsed_uri or parsed_uri.endswith(dot_no_proxy_uri):
                return True
    return False


def _resolve_proxy(
    config: dict[str, Any], init_config: dict[str, Any]
) -> tuple[dict[str, str] | None, list[str] | None]:
    """Resolve proxy settings with the RequestsWrapper precedence: instance, then init_config, then Agent config."""
    if is_affirmative(config['skip_proxy']):
        return PROXY_SETTINGS_DISABLED.copy(), None
    proxies = config['proxy'] or init_config.get('proxy')
    if not proxies and is_affirmative(init_config.get('use_agent_proxy', True)):
        proxies = datadog_agent.get_config('proxy')
    if not proxies:
        return None, None
    proxies = proxies.copy()
    no_proxy = proxies.pop('no_proxy', None)
    if isinstance(no_proxy, str):
        no_proxy = [host.strip() for host in no_proxy.replace(';', ',').split(',') if host.strip()]
    # A proxy block carrying only no_proxy has no explicit proxy URL to route through, but the
    # no_proxy list is retained so it can be applied against an environment proxy (HTTP_PROXY etc.).
    if not proxies:
        return None, no_proxy
    return proxies, no_proxy


class _ProxyRoutingTransport(httpx2.BaseTransport):
    """Pick a proxied or direct transport per request, mirroring RequestsWrapper's per-request no_proxy check."""

    def __init__(
        self,
        scheme_transports: dict[str, httpx2.BaseTransport],
        direct: httpx2.BaseTransport,
        no_proxy_uris: list[str] | None,
        env_schemes: set[str] | None = None,
        env_no_proxy: list[str] | None = None,
    ) -> None:
        self._scheme_transports = scheme_transports
        self._direct = direct
        self._no_proxy_uris = no_proxy_uris
        # Schemes whose proxy was filled from the environment, and the env NO_PROXY that governs only them.
        self._env_schemes = env_schemes or set()
        self._env_no_proxy = env_no_proxy or []

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        url = str(request.url)
        scheme = request.url.scheme
        # Tier 1: an explicit no_proxy bypasses every proxy, mirroring RequestsWrapper's own per-request check.
        if self._no_proxy_uris and should_bypass_proxy(url, self._no_proxy_uris):
            return self._direct.handle_request(request)
        transport = self._scheme_transports.get(scheme)
        if transport is None:
            return self._direct.handle_request(request)
        # Tier 2: env NO_PROXY only diverts schemes filled from the environment, never an explicit proxy.
        # Matching mirrors RequestsWrapper's should_bypass_proxy (host/CIDR), not httpx's URL-pattern mounts.
        if scheme in self._env_schemes and self._env_no_proxy and should_bypass_proxy(url, self._env_no_proxy):
            return self._direct.handle_request(request)
        return transport.handle_request(request)

    def close(self) -> None:
        seen = {id(self._direct): self._direct}
        seen.update({id(t): t for t in self._scheme_transports.values()})
        for transport in seen.values():
            transport.close()


def _build_proxy_transport(
    proxies: dict[str, str] | None,
    no_proxy: list[str] | None,
    verify: bool | str,
    cert: str | tuple[str, str] | None,
    *,
    env_schemes: set[str] | None = None,
    env_no_proxy: list[str] | None = None,
) -> _ProxyRoutingTransport | None:
    """Build the per-request routing transport, or None when no real proxy is configured.

    env_schemes/env_no_proxy carry the two-tier NO_PROXY contract and are supplied only by
    _build_env_proxy_transport; direct callers leave them unset.
    """
    # None => no custom transport; the client builds its default and trust_env decides env proxies.
    if not proxies or proxies == PROXY_SETTINGS_DISABLED:
        return None
    cache: dict[str, httpx2.BaseTransport] = {}
    scheme_transports: dict[str, httpx2.BaseTransport] = {}
    for scheme in ('http', 'https'):
        url = proxies.get(scheme)
        if not url:
            continue
        if url not in cache:
            cache[url] = httpx2.HTTPTransport(proxy=httpx2.Proxy(url), verify=verify, cert=cert)
        scheme_transports[scheme] = cache[url]
    if not scheme_transports:
        return None
    direct = httpx2.HTTPTransport(verify=verify, cert=cert)
    return _ProxyRoutingTransport(scheme_transports, direct, no_proxy, env_schemes, env_no_proxy)


def _env_proxies() -> dict[str, str]:
    """Read http/https proxy URLs from the environment, via httpx2's own resolver for name/case parity."""
    mounts = get_environment_proxies()
    fallback = mounts.get('all://')
    proxies: dict[str, str] = {}
    for scheme in ('http', 'https'):
        url = mounts.get(f'{scheme}://') or fallback
        if url:
            proxies[scheme] = url
    return proxies


def _env_no_proxy() -> list[str]:
    """Return the environment NO_PROXY hosts as bypass patterns for should_bypass_proxy."""
    # Raw NO_PROXY from stdlib getproxies(), not get_environment_proxies, so CIDR survives for should_bypass_proxy.
    raw = getproxies().get('no', '')
    return [host.strip() for host in raw.replace(';', ',').split(',') if host.strip()]


def _build_env_proxy_transport(
    instance_proxies: dict[str, str] | None,
    no_proxy: list[str] | None,
    verify: bool | str,
    cert: str | tuple[str, str] | None,
) -> _ProxyRoutingTransport | None:
    """Fill the schemes the instance left unset from the environment; instance entries win per scheme."""
    env = _env_proxies()
    instance_proxies = instance_proxies or {}
    merged = {**env, **instance_proxies}
    if not merged:
        return None
    env_schemes = {scheme for scheme in env if not instance_proxies.get(scheme)}
    env_no_proxy = _env_no_proxy() if env_schemes else []
    return _build_proxy_transport(merged, no_proxy, verify, cert, env_schemes=env_schemes, env_no_proxy=env_no_proxy)


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
            raise HTTPStatusError(
                str(exc) or exc.__class__.__name__,
                request=getattr(exc, 'request', None),
                response=self,
            ) from exc

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
        'auth_token_handler',
        'logger',
        'no_proxy_uris',
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
        proxies, no_proxy = _resolve_proxy(config, init_config)
        # Exposed for parity with RequestsWrapper, which http_check reads as self.http.no_proxy_uris.
        self.no_proxy_uris = no_proxy or None

        # options['headers'] is the per-request source of truth and is re-read in _build_request_kwargs,
        # so direct mutation (__setitem__, update(), whole-dict replacement) reaches the wire.
        # set_header mutates options['headers'] in place; the per-request merge above re-reads it.
        self.options: dict[str, Any] = {
            'auth': auth,
            'cert': cert,
            'headers': headers,
            'proxies': proxies,
            'timeout': timeout,
            'verify': verify,
            'allow_redirects': allow_redirects,
        }

        self.auth_token_handler = (
            create_auth_token_handler(config['auth_token']) if config['auth_token'] is not None else None
        )

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
        default_fields['skip_proxy'] = init_config.get('skip_proxy', default_fields['skip_proxy'])
        default_fields['timeout'] = init_config.get('timeout', default_fields['timeout'])

        config = {field: instance.get(field, value) for field, value in default_fields.items()}

        remapper = dict(remapper) if remapper else {}
        # DEFAULT_REMAPPED_FIELDS intentionally wins over caller entries, matching http.py:282.
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

    def _build_client(self, transport: httpx2.BaseTransport | None) -> httpx2.Client:
        proxies = self.options['proxies']
        # An injected transport (e.g. tests) wins; otherwise build one router that owns all proxy resolution:
        # instance schemes, env-filled schemes, and the no_proxy bypass. skip_proxy installs no router.
        router = None
        if transport is None and proxies != PROXY_SETTINGS_DISABLED and (proxies or self.no_proxy_uris):
            router = _build_env_proxy_transport(
                proxies, self.no_proxy_uris, self.options['verify'], self.options['cert']
            )
            transport = router
        # trust_env is off only when our router owns proxy resolution or skip_proxy is set.
        trust_env = router is None and proxies != PROXY_SETTINGS_DISABLED
        kwargs: dict[str, Any] = {
            'headers': self.options['headers'],
            'timeout': _make_timeout(self.options['timeout'][0], self.options['timeout'][1]),
            'follow_redirects': self.options['allow_redirects'],
            'verify': self.options['verify'],
            'trust_env': trust_env,
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
        for key in list(self.options['headers']):
            if key.lower() == name.lower():
                self.options['headers'][key] = value
                return
        self.options['headers'][name] = value

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

    def handle_auth_token(self, **request: Any) -> None:
        if self.auth_token_handler is not None:
            try:
                self.auth_token_handler.poll(**request)
            except (httpx2.HTTPError, httpx2.InvalidURL) as exc:
                raise _map_httpx2_exception(exc) from exc

    def _request(self, method: str, url: str, options: dict[str, Any]) -> HTTPX2ResponseAdapter:
        # stream=True keeps the connection open until the body is consumed (.content/.text/.iter_*)
        # or close() is called. Callers should use it as a context manager when not reading the body.
        if self._log_requests:
            self.logger.debug('Sending %s request to %s', method, url)

        follow_redirects = (
            bool(options['follow_redirects']) if 'follow_redirects' in options else httpx2.USE_CLIENT_DEFAULT
        )
        auth = options['auth'] if 'auth' in options else httpx2.USE_CLIENT_DEFAULT

        # Poll before building kwargs so the writer's header mutation is re-read into the per-request merge.
        self.handle_auth_token(method=method, url=url, default_options=self.options)
        request_kwargs = self._build_request_kwargs(options, method=method, url=url)

        if self.auth_token_handler is None:
            return self._send_once(method, url, request_kwargs, follow_redirects, auth)

        # With a handler, send once, raise_for_status, and renew-and-retry once on any error (http.py:522-531).
        response = None
        try:
            response = self._send_once(method, url, request_kwargs, follow_redirects, auth)
            response.raise_for_status()
            return response
        except Exception as e:
            self.logger.debug('Renewing auth token, as an error occurred: %s', e)
            # Close the streamed first response (if any) before retrying, or the connection leaks.
            if response is not None:
                response.close()
            # Re-poll with an error marker to force a fresh token, then rebuild kwargs so the new header
            # reaches the wire. The retry response is returned without a second raise_for_status (http.py:529).
            self.handle_auth_token(method=method, url=url, default_options=self.options, error=str(e))
            request_kwargs = self._build_request_kwargs(options, method=method, url=url)
            return self._send_once(method, url, request_kwargs, follow_redirects, auth)

    def _send_once(
        self,
        method: str,
        url: str,
        request_kwargs: dict[str, Any],
        follow_redirects: Any,
        auth: Any,
    ) -> HTTPX2ResponseAdapter:
        try:
            request = self._client.build_request(method, url, **request_kwargs)
            response = self._client.send(request, stream=True, follow_redirects=follow_redirects, auth=auth)
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


def _parse_expires_in(token_expiration: Any) -> int | float | str | None:
    # Ported verbatim from http.py:1115. The caller relies on a non-number falling through to a
    # `+=` TypeError, so a string like 'two minutes' is returned unchanged rather than coerced.
    if isinstance(token_expiration, int) or isinstance(token_expiration, float):
        return token_expiration
    if isinstance(token_expiration, str):
        try:
            token_expiration = int(token_expiration)
        except ValueError:
            LOGGER.debug('Could not convert %s to an integer', token_expiration)
    else:
        LOGGER.debug('Unexpected type for `expires_in`: %s.', type(token_expiration))
        token_expiration = None
    return token_expiration


def _build_oauth_client() -> httpx2.Client:
    """Standalone client for the OAuth token fetch: default TLS, no wrapper proxy, matching RequestsWrapper parity."""
    return httpx2.Client()


def create_auth_token_handler(config: Any) -> AuthTokenHandler:
    if not isinstance(config, dict):
        raise ConfigurationError('The `auth_token` field must be a mapping')
    elif 'reader' not in config or 'writer' not in config:
        raise ConfigurationError('The `auth_token` field must define both `reader` and `writer` settings')

    config = deepcopy(config)

    reader_config = config['reader']
    if not isinstance(reader_config, dict):
        raise ConfigurationError('The `reader` settings of field `auth_token` must be a mapping')

    writer_config = config['writer']
    if not isinstance(writer_config, dict):
        raise ConfigurationError('The `writer` settings of field `auth_token` must be a mapping')

    reader_type = reader_config.pop('type', '')
    if not isinstance(reader_type, str):
        raise ConfigurationError('The reader `type` of field `auth_token` must be a string')
    elif not reader_type:
        raise ConfigurationError('The reader `type` of field `auth_token` is required')
    elif reader_type in DEFERRED_AUTH_TOKEN_READERS:
        raise ConfigurationError(
            'The `{}` reader of field `auth_token` is not yet supported by the httpx2 client'.format(reader_type)
        )
    elif reader_type not in AUTH_TOKEN_READERS:
        raise ConfigurationError(
            'Unknown `auth_token` reader type, must be one of: {}'.format(', '.join(sorted(AUTH_TOKEN_READERS)))
        )

    writer_type = writer_config.pop('type', '')
    if not isinstance(writer_type, str):
        raise ConfigurationError('The writer `type` of field `auth_token` must be a string')
    elif not writer_type:
        raise ConfigurationError('The writer `type` of field `auth_token` is required')
    elif writer_type not in AUTH_TOKEN_WRITERS:
        raise ConfigurationError(
            'Unknown `auth_token` writer type, must be one of: {}'.format(', '.join(sorted(AUTH_TOKEN_WRITERS)))
        )

    reader = AUTH_TOKEN_READERS[reader_type](reader_config)
    writer = AUTH_TOKEN_WRITERS[writer_type](writer_config)

    return AuthTokenHandler(reader, writer)


class AuthTokenHandler:
    def __init__(self, reader: Any, writer: Any) -> None:
        self.reader = reader
        self.writer = writer

    def poll(self, **request: Any) -> None:
        token = self.reader.read(**request)
        if token is not None:
            self.writer.write(token, **request)


class AuthTokenFileReader:
    def __init__(self, config: dict[str, Any]) -> None:
        self._path = config.get('path', '')
        if not isinstance(self._path, str):
            raise ConfigurationError('The `path` setting of `auth_token` reader must be a string')
        elif not self._path:
            raise ConfigurationError('The `path` setting of `auth_token` reader is required')

        pattern = config.get('pattern')
        self._pattern: re.Pattern[str] | None = None
        if pattern is not None:
            if not isinstance(pattern, str):
                raise ConfigurationError('The `pattern` setting of `auth_token` reader must be a string')
            self._pattern = re.compile(pattern)
            if self._pattern.groups != 1:
                raise ValueError(
                    'The pattern `{}` setting of `auth_token` reader must define exactly one group'.format(
                        self._pattern.pattern
                    )
                )

        # Cache the token between requests; re-read only on first use or when an error marker forces a refresh.
        self._token: str | None = None

    def read(self, **request: Any) -> str | None:
        if self._token is None or 'error' in request:
            with open(self._path, encoding='utf-8') as f:
                content = f.read()

            if self._pattern is None:
                self._token = content.strip()
            else:
                match = self._pattern.search(content)
                if not match:
                    raise ValueError(
                        'The pattern `{}` does not match anything in file: {}'.format(self._pattern.pattern, self._path)
                    )
                self._token = match.group(1)

            return self._token
        return None


class AuthTokenOAuthReader:
    def __init__(self, config: dict[str, Any]) -> None:
        self._url = config.get('url', '')
        if not isinstance(self._url, str):
            raise ConfigurationError('The `url` setting of `auth_token` reader must be a string')
        elif not self._url:
            raise ConfigurationError('The `url` setting of `auth_token` reader is required')

        self._client_id = config.get('client_id', '')
        if not isinstance(self._client_id, str):
            raise ConfigurationError('The `client_id` setting of `auth_token` reader must be a string')
        elif not self._client_id:
            raise ConfigurationError('The `client_id` setting of `auth_token` reader is required')

        self._client_secret = config.get('client_secret', '')
        if not isinstance(self._client_secret, str):
            raise ConfigurationError('The `client_secret` setting of `auth_token` reader must be a string')
        elif not self._client_secret:
            raise ConfigurationError('The `client_secret` setting of `auth_token` reader is required')

        self._basic_auth = config.get('basic_auth', False)
        if not isinstance(self._basic_auth, bool):
            raise ConfigurationError('The `basic_auth` setting of `auth_token` reader must be a boolean')

        options = config.get('options', {})
        self._options: dict[str, Any] = options if isinstance(options, dict) else {}

        self._token: str | None = None
        self._expiration: float = 0

    def read(self, **request: Any) -> str | None:
        if self._token is None or get_timestamp() >= self._expiration or 'error' in request:
            data: dict[str, Any] = {'grant_type': 'client_credentials', **self._options}
            auth = None
            if self._basic_auth:
                auth = httpx2.BasicAuth(self._client_id, self._client_secret)
            else:
                data['client_id'] = self._client_id
                data['client_secret'] = self._client_secret

            with _build_oauth_client() as client:
                token = client.post(self._url, data=data, auth=auth).json()

            # https://www.rfc-editor.org/rfc/rfc6749#section-5.2
            if 'error' in token:
                raise Exception('OAuth2 client credentials grant error: {}'.format(token['error']))

            # https://www.rfc-editor.org/rfc/rfc6749#section-4.4.3
            self._token = token['access_token']
            # `expires_in` is optional per https://www.rfc-editor.org/rfc/rfc6749#section-5.1, and a
            # non-numeric value falls back to DEFAULT_EXPIRATION (parity with http.py:981-989).
            expires_in = _parse_expires_in(token.get('expires_in'))
            if not isinstance(expires_in, (int, float)):
                LOGGER.debug(
                    'The `expires_in` field of the OAuth2 response is not a number, defaulting to %s',
                    DEFAULT_EXPIRATION,
                )
                expires_in = DEFAULT_EXPIRATION
            self._expiration = get_timestamp() + expires_in
            return self._token
        return None


class AuthTokenHeaderWriter:
    DEFAULT_PLACEHOLDER = '<TOKEN>'

    def __init__(self, config: dict[str, Any]) -> None:
        self._name = config.get('name', '')
        if not isinstance(self._name, str):
            raise ConfigurationError('The `name` setting of `auth_token` writer must be a string')
        elif not self._name:
            raise ConfigurationError('The `name` setting of `auth_token` writer is required')

        self._value = config.get('value', self.DEFAULT_PLACEHOLDER)
        if not isinstance(self._value, str):
            raise ConfigurationError('The `value` setting of `auth_token` writer must be a string')

        self._placeholder = config.get('placeholder', self.DEFAULT_PLACEHOLDER)
        if not isinstance(self._placeholder, str):
            raise ConfigurationError('The `placeholder` setting of `auth_token` writer must be a string')
        elif not self._placeholder:
            raise ConfigurationError('The `placeholder` setting of `auth_token` writer cannot be an empty string')
        elif self._placeholder not in self._value:
            raise ConfigurationError(
                'The `value` setting of `auth_token` writer does not contain the placeholder string `{}`'.format(
                    self._placeholder
                )
            )

    def write(self, token: str, **request: Any) -> None:
        request['default_options']['headers'][self._name] = self._value.replace(self._placeholder, token, 1)


AUTH_TOKEN_READERS = {'file': AuthTokenFileReader, 'oauth': AuthTokenOAuthReader}
AUTH_TOKEN_WRITERS = {'header': AuthTokenHeaderWriter}
# Recognized but deferred long-tail readers: named here so they get a clear error instead of the
# generic unknown-type message, which therefore lists only the supported `file, oauth`.
DEFERRED_AUTH_TOKEN_READERS = frozenset({'dcos_auth'})
