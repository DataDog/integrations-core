# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
HTTP client wrapper backed by httpx, exposing the same public API as RequestsWrapper.
Used when a check opts in via the base check's use_httpx option.
"""

from __future__ import annotations

import logging
from collections import ChainMap
from contextlib import ExitStack
from urllib.parse import unquote, urlparse

import httpx
from binary import KIBIBYTE

from datadog_checks.base.agent import datadog_agent
from datadog_checks.base.config import is_affirmative
from datadog_checks.base.utils.headers import get_default_headers, update_headers
from datadog_checks.base.utils.tls import SUPPORTED_PROTOCOL_VERSIONS, create_ssl_context

from .http import (
    DEFAULT_REMAPPED_FIELDS,
    PROXY_SETTINGS_DISABLED,
    STANDARD_FIELDS,
    create_auth_token_handler,
    get_tls_config_from_options,
    handle_kerberos_cache,
    handle_kerberos_keytab,
    is_uds_url,
    quote_uds_url,
    should_bypass_proxy,
)

LOGGER = logging.getLogger(__name__)


class HTTPXResponseAdapter:
    """
    Wraps httpx.Response to expose the same surface as the requests Response
    used by ResponseWrapper, so callers can use response.content, response.iter_lines(),
    response.encoding, etc. unchanged.
    """

    def __init__(self, response: httpx.Response, default_chunk_size: int) -> None:
        self._response = response
        self._default_chunk_size = default_chunk_size
        self._content: bytes | None = None

    @property
    def content(self) -> bytes:
        if self._content is None:
            self._content = self._response.content
        return self._content

    @property
    def headers(self):
        return self._response.headers

    @property
    def encoding(self) -> str | None:
        return self._response.encoding

    @encoding.setter
    def encoding(self, value: str | None) -> None:
        self._response.encoding = value

    @property
    def status_code(self) -> int:
        return self._response.status_code

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False):
        size = chunk_size if chunk_size is not None else self._default_chunk_size
        content = self.content
        for i in range(0, len(content), size):
            chunk = content[i : i + size]
            if decode_unicode:
                enc = self._response.encoding or 'utf-8'
                yield chunk.decode(enc, errors='replace')
            else:
                yield chunk

    def iter_lines(self, chunk_size: int | None = None, decode_unicode: bool = False, delimiter: bytes | None = None):
        content = self.content
        delim = delimiter if delimiter is not None else b'\n'
        if delim == b'\n':
            start = 0
            while start < len(content):
                end = content.find(b'\n', start)
                if end == -1:
                    line = content[start:]
                    if line:
                        out = (
                            line.decode(self._response.encoding or 'utf-8', errors='replace')
                            if decode_unicode
                            else line
                        )
                        yield out
                    break
                if end > 0 and content[end - 1 : end] == b'\r':
                    line = content[start : end - 1]
                else:
                    line = content[start:end]
                start = end + 1
                out = line.decode(self._response.encoding or 'utf-8', errors='replace') if decode_unicode else line
                yield out
        else:
            start = 0
            while start < len(content):
                end = content.find(delim, start)
                if end == -1:
                    part = content[start:]
                    if part:
                        out = (
                            part.decode(self._response.encoding or 'utf-8', errors='replace')
                            if decode_unicode
                            else part
                        )
                        yield out
                    break
                part = content[start:end]
                start = end + len(delim)
                out = part.decode(self._response.encoding or 'utf-8', errors='replace') if decode_unicode else part
                yield out

    def json(self, **kwargs):
        return self._response.json(**kwargs)

    def raise_for_status(self) -> None:
        from requests.exceptions import HTTPError as RequestsHTTPError

        if 400 <= self._response.status_code:
            msg = '{} Client Error for url'.format(self._response.status_code)
            try:
                reason = getattr(self._response, 'reason_phrase', None) or ''
                url = getattr(self._response, 'url', '') or ''
                if reason or url:
                    msg = '{} {} for url: {}'.format(self._response.status_code, reason, url)
            except (RuntimeError, AttributeError):
                pass
            raise RequestsHTTPError(msg, response=self)

    def close(self) -> None:
        self._response.close()


def _make_httpx_auth(config: dict, logger: logging.Logger):
    """Build httpx-compatible auth from config. Supports basic; others fall back to None with warning."""
    auth_type = config.get('auth_type', 'basic').lower()
    if auth_type == 'basic':
        if config.get('username') is not None and config.get('password') is not None:
            return (config['username'], config['password'])
        return None
    logger.warning(
        'HTTPXWrapper does not yet support auth_type=%s; request will be sent without auth.',
        auth_type,
    )
    return None


def _parse_uds_url(url: str) -> tuple[str | None, str]:
    """Return (uds_path, request_url) for unix:// URLs, or (None, url) for normal URLs."""
    if not is_uds_url(url):
        return None, url
    parsed = urlparse(url)
    netloc = parsed.netloc
    path = parsed.path or '/'
    if netloc:
        uds_path = unquote(netloc)
    else:
        uds_path_head, has_dot_sock, path_suffix = (parsed.path or '/').partition('.sock')
        if has_dot_sock:
            uds_path = uds_path_head + '.sock'
            path = path_suffix or '/'
        else:
            uds_path = parsed.path or '/'
            path = '/'
    return uds_path, 'http://localhost' + path


class _HTTPXSessionLike:
    """Minimal session-like object for backward compatibility with code that calls self.http.session.close()."""

    __slots__ = ('_wrapper',)

    def __init__(self, wrapper: 'HTTPXWrapper') -> None:
        self._wrapper = wrapper

    def close(self) -> None:
        if getattr(self._wrapper, '_client', None) is not None:
            self._wrapper._client.close()
            self._wrapper._client = None


class HTTPXWrapper:
    """
    HTTP client wrapper backed by httpx, exposing the same public API as RequestsWrapper
    so that AgentCheck.http and other callers can use it interchangeably when use_httpx is True.
    """

    __slots__ = (
        '_client',
        'tls_use_host_header',
        'ignore_tls_warning',
        'log_requests',
        'logger',
        'no_proxy_uris',
        'options',
        'persist_connections',
        'request_hooks',
        'auth_token_handler',
        'request_size',
        'tls_protocols_allowed',
        'tls_config',
    )

    def __init__(
        self,
        instance: dict,
        init_config: dict,
        remapper: dict | None = None,
        logger: logging.Logger | None = None,
        session: None = None,
    ) -> None:
        self.logger = logger or LOGGER
        default_fields = dict(STANDARD_FIELDS)
        default_fields['log_requests'] = init_config.get('log_requests', default_fields['log_requests'])
        default_fields['skip_proxy'] = init_config.get('skip_proxy', default_fields['skip_proxy'])
        default_fields['timeout'] = init_config.get('timeout', default_fields['timeout'])
        default_fields['tls_ignore_warning'] = init_config.get(
            'tls_ignore_warning', default_fields['tls_ignore_warning']
        )

        config = {field: instance.get(field, value) for field, value in default_fields.items()}

        if remapper is None:
            remapper = {}
        remapper = dict(remapper)
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

        connect_timeout = read_timeout = float(config['timeout'])
        if config['connect_timeout'] is not None:
            connect_timeout = float(config['connect_timeout'])
        if config['read_timeout'] is not None:
            read_timeout = float(config['read_timeout'])

        headers = get_default_headers()
        if config['headers']:
            headers.clear()
            update_headers(headers, config['headers'])
        if config['extra_headers']:
            update_headers(headers, config['extra_headers'])

        self.tls_use_host_header = is_affirmative(config['tls_use_host_header']) and 'Host' in headers

        auth = _make_httpx_auth(config, self.logger)
        allow_redirects = is_affirmative(config['allow_redirects'])

        verify: bool | str = True
        if isinstance(config['tls_ca_cert'], str):
            verify = config['tls_ca_cert']
        elif not is_affirmative(config['tls_verify']):
            verify = False

        cert = None
        if isinstance(config['tls_cert'], str):
            if isinstance(config['tls_private_key'], str):
                cert = (config['tls_cert'], config['tls_private_key'])
            else:
                cert = config['tls_cert']

        no_proxy_uris = None
        if is_affirmative(config['skip_proxy']):
            proxies = PROXY_SETTINGS_DISABLED.copy()
        else:
            proxies = config['proxy'] or init_config.get('proxy')
            if not proxies and is_affirmative(init_config.get('use_agent_proxy', True)):
                proxies = datadog_agent.get_config('proxy')
            if proxies:
                proxies = proxies.copy()
                if 'no_proxy' in proxies:
                    no_proxy_uris = proxies.pop('no_proxy')
                    if isinstance(no_proxy_uris, str):
                        no_proxy_uris = no_proxy_uris.replace(';', ',').split(',')
            else:
                proxies = None

        self.options = {
            'auth': auth,
            'cert': cert,
            'headers': headers,
            'proxies': proxies,
            'timeout': (connect_timeout, read_timeout),
            'verify': verify,
            'allow_redirects': allow_redirects,
        }
        self.no_proxy_uris = no_proxy_uris
        self.ignore_tls_warning = is_affirmative(config['tls_ignore_warning'])
        self.request_size = int(float(config['request_size']) * KIBIBYTE)

        self.tls_protocols_allowed = [p for p in config['tls_protocols_allowed'] if p in SUPPORTED_PROTOCOL_VERSIONS]
        for protocol in config['tls_protocols_allowed']:
            if protocol not in SUPPORTED_PROTOCOL_VERSIONS:
                self.logger.warning('Unknown protocol `%s` configured, ignoring it.', protocol)

        self.persist_connections = self.tls_use_host_header or is_affirmative(config['persist_connections'])
        self._client: httpx.Client | None = None

        self.log_requests = is_affirmative(config['log_requests'])
        if config['auth_token'] is not None:
            self.auth_token_handler = create_auth_token_handler(config['auth_token'])
        else:
            self.auth_token_handler = None

        self.request_hooks = []
        if config.get('kerberos_keytab'):
            self.request_hooks.append(lambda: handle_kerberos_keytab(config['kerberos_keytab']))
        if config.get('kerberos_cache'):
            self.request_hooks.append(lambda: handle_kerberos_cache(config['kerberos_cache']))

        self.tls_config = {k: v for k, v in config.items() if k.startswith('tls_')}

    @property
    def session(self) -> _HTTPXSessionLike:
        return _HTTPXSessionLike(self)

    def get(self, url: str, **options):
        return self._request('get', url, options)

    def post(self, url: str, **options):
        return self._request('post', url, options)

    def head(self, url: str, **options):
        return self._request('head', url, options)

    def put(self, url: str, **options):
        return self._request('put', url, options)

    def patch(self, url: str, **options):
        return self._request('patch', url, options)

    def delete(self, url: str, **options):
        return self._request('delete', url, options)

    def options_method(self, url: str, **options):
        return self._request('options', url, options)

    def handle_auth_token(self, **request) -> None:
        if self.auth_token_handler is not None:
            self.auth_token_handler.poll(**request)

    def _request(self, method: str, url: str, options: dict):
        if self.log_requests:
            self.logger.debug('Sending %s request to %s', method.upper(), url)

        if self.no_proxy_uris and should_bypass_proxy(url, self.no_proxy_uris):
            options = dict(options)
            options['proxies'] = PROXY_SETTINGS_DISABLED

        persist = options.pop('persist', None)
        if persist is None:
            persist = self.persist_connections

        new_options = ChainMap(options, self.options)

        if url.startswith('https') and not self.ignore_tls_warning and not new_options['verify']:
            self.logger.debug('An unverified HTTPS request is being made to %s', url)

        extra_headers = options.pop('extra_headers', None)

        uds_path, request_url = _parse_uds_url(url)
        if uds_path:
            url = quote_uds_url(url)

        self.handle_auth_token(method=method, url=url, default_options=self.options)

        with ExitStack() as stack:
            for hook in self.request_hooks:
                stack.enter_context(hook())

            tls_config = ChainMap(get_tls_config_from_options(dict(new_options)), self.tls_config)
            verify = new_options['verify']
            if isinstance(verify, str):
                verify = create_ssl_context(dict(tls_config))
            elif verify is True:
                verify = create_ssl_context(dict(tls_config))

            timeout = new_options['timeout']
            if isinstance(timeout, (list, tuple)) and len(timeout) == 2:
                timeout_httpx = httpx.Timeout(timeout[0], read=timeout[1])
            else:
                timeout_httpx = httpx.Timeout(timeout)

            proxies = new_options['proxies']
            proxy_url = None
            if proxies and proxies != PROXY_SETTINGS_DISABLED:
                if url.startswith('https'):
                    proxy_url = proxies.get('https') or proxies.get('http')
                else:
                    proxy_url = proxies.get('http')
                if not isinstance(proxy_url, str) or not proxy_url:
                    proxy_url = None

            def _request_headers():
                h = dict(new_options['headers']) if new_options['headers'] else {}
                if extra_headers:
                    h.update(extra_headers)
                return h

            auth = new_options['auth']
            cert = new_options['cert']

            request_kwargs: dict = {}
            for key in ('json', 'content', 'data', 'files'):
                if key in new_options:
                    request_kwargs[key] = new_options[key]

            if uds_path:
                transport = httpx.HTTPTransport(uds=uds_path, verify=verify, cert=cert)
                client = httpx.Client(
                    transport=transport,
                    timeout=timeout_httpx,
                    follow_redirects=new_options['allow_redirects'],
                    auth=auth,
                    trust_env=False,
                )
                try:
                    if self.auth_token_handler:
                        try:
                            response = client.request(
                                method.upper(), request_url, headers=_request_headers(), **request_kwargs
                            )
                            response.raise_for_status()
                        except Exception as e:
                            self.logger.debug('Renewing auth token, as an error occurred: %s', e)
                            self.handle_auth_token(method=method, url=url, default_options=self.options, error=str(e))
                            response = client.request(
                                method.upper(), request_url, headers=_request_headers(), **request_kwargs
                            )
                    else:
                        response = client.request(
                            method.upper(), request_url, headers=_request_headers(), **request_kwargs
                        )
                    return HTTPXResponseAdapter(response, self.request_size)
                finally:
                    client.close()
            else:
                if persist and self._client is not None:
                    client = self._client
                else:
                    client = httpx.Client(
                        verify=verify,
                        cert=cert,
                        timeout=timeout_httpx,
                        follow_redirects=new_options['allow_redirects'],
                        auth=auth,
                        proxy=proxy_url,
                        trust_env=False,
                    )
                    if persist:
                        self._client = client
                    else:
                        stack.enter_context(client)

                if self.auth_token_handler:
                    try:
                        response = client.request(
                            method.upper(), request_url, headers=_request_headers(), **request_kwargs
                        )
                        response.raise_for_status()
                    except Exception as e:
                        self.logger.debug('Renewing auth token, as an error occurred: %s', e)
                        self.handle_auth_token(method=method, url=url, default_options=self.options, error=str(e))
                        response = client.request(
                            method.upper(), request_url, headers=_request_headers(), **request_kwargs
                        )
                else:
                    response = client.request(method.upper(), request_url, headers=_request_headers(), **request_kwargs)

                return HTTPXResponseAdapter(response, self.request_size)

    def __del__(self) -> None:
        try:
            if getattr(self, '_client', None) is not None:
                self._client.close()
        except AttributeError:
            pass
