# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
from typing import Any, Iterator

import httpx

from datadog_checks.base.config import is_affirmative
from datadog_checks.base.utils.headers import get_default_headers, update_headers

from .http_exceptions import (
    HTTPConnectionError,
    HTTPError,
    HTTPRequestError,
    HTTPStatusError,
    HTTPTimeoutError,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10

# Fields recognized from instance/init_config for httpx client construction
_STANDARD_FIELDS = {
    'allow_redirects': True,
    'auth_type': 'basic',
    'connect_timeout': None,
    'extra_headers': None,
    'headers': None,
    'kerberos_auth': None,
    'kerberos_delegate': False,
    'kerberos_force_initiate': False,
    'kerberos_hostname': None,
    'kerberos_keytab': None,
    'kerberos_principal': None,
    'ntlm_domain': None,
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

# Legacy field aliases applied before reading standard fields
_DEFAULT_REMAPPED_FIELDS = {
    'kerberos': {'name': 'kerberos_auth'},
    'no_proxy': {'name': 'skip_proxy'},
}


def _build_httpx_client(
    instance: dict,
    init_config: dict,
    remapper: dict | None = None,
    logger: logging.Logger | None = None,
) -> httpx.Client:
    log = logger or LOGGER

    # Merge default fields; init_config provides global overrides
    default_fields = dict(_STANDARD_FIELDS)
    default_fields['skip_proxy'] = init_config.get('skip_proxy', default_fields['skip_proxy'])
    default_fields['timeout'] = init_config.get('timeout', default_fields['timeout'])

    # Populate config from instance, using defaults for missing fields
    config = {field: instance.get(field, value) for field, value in default_fields.items()}

    # Apply remapper: normalize legacy/integration-specific field names
    if remapper is None:
        remapper = {}
    remapper.update(_DEFAULT_REMAPPED_FIELDS)

    for remapped_field, data in remapper.items():
        field = data.get('name')
        if field not in _STANDARD_FIELDS:
            continue
        # Standard field already explicitly set — skip remapped alias
        if field in instance:
            continue
        default = default_fields[field]
        if data.get('invert'):
            default = not default
        value = instance.get(remapped_field, data.get('default', default))
        if data.get('invert'):
            value = not is_affirmative(value)
        config[field] = value

    # --- Timeouts ---
    connect_timeout = read_timeout = float(config['timeout'])
    if config['connect_timeout'] is not None:
        connect_timeout = float(config['connect_timeout'])
    if config['read_timeout'] is not None:
        read_timeout = float(config['read_timeout'])
    # read_timeout is the default; connect overrides the connect-phase only
    timeout = httpx.Timeout(read_timeout, connect=connect_timeout)

    # --- Headers ---
    headers = get_default_headers()
    if config['headers']:
        headers.clear()
        update_headers(headers, config['headers'])
    if config['extra_headers']:
        update_headers(headers, config['extra_headers'])

    # --- Auth ---
    auth_type = (config['auth_type'] or 'basic').lower()
    if auth_type == 'basic':
        if config['kerberos_auth']:
            log.warning(
                'The ability to use Kerberos auth without explicitly setting auth_type to '
                '`kerberos` is deprecated and will be removed in Agent 8'
            )
            auth_type = 'kerberos'
        elif config['ntlm_domain']:
            log.warning(
                'The ability to use NTLM auth without explicitly setting auth_type to '
                '`ntlm` is deprecated and will be removed in Agent 8'
            )
            auth_type = 'ntlm'

    auth: httpx.Auth | None = None
    if auth_type == 'basic':
        if config['username'] is not None:
            auth = httpx.BasicAuth(config['username'], config['password'] or '')
    elif auth_type == 'digest':
        if config['username'] is not None:
            auth = httpx.DigestAuth(config['username'], config['password'] or '')
    elif auth_type == 'kerberos':
        from datadog_checks.base.utils.httpx_auth import KerberosAuth

        auth = KerberosAuth(
            mutual_authentication=config.get('kerberos_auth') or 'required',
            delegate=is_affirmative(config['kerberos_delegate']),
            force_preemptive=is_affirmative(config['kerberos_force_initiate']),
            hostname_override=config['kerberos_hostname'],
            principal=config['kerberos_principal'],
            keytab=config['kerberos_keytab'],
        )
    elif auth_type == 'ntlm':
        from datadog_checks.base.utils.httpx_auth import NTLMAuth

        auth = NTLMAuth(config['ntlm_domain'], config['password'])

    # --- TLS / verify ---
    verify: bool | str = True
    if isinstance(config['tls_ca_cert'], str):
        verify = config['tls_ca_cert']
    elif not is_affirmative(config['tls_verify']):
        verify = False

    cert: tuple[str, str] | str | None = None
    if isinstance(config['tls_cert'], str):
        if isinstance(config['tls_private_key'], str):
            cert = (config['tls_cert'], config['tls_private_key'])
        else:
            cert = config['tls_cert']

    # --- Proxies ---
    # trust_env=True lets httpx fall back to HTTP_PROXY/HTTPS_PROXY env vars (same as requests)
    trust_env = True
    mounts: dict[str, httpx.BaseTransport | None] | None = None

    if is_affirmative(config['skip_proxy']):
        trust_env = False
    else:
        raw_proxy = config['proxy'] or init_config.get('proxy')
        if raw_proxy:
            mounts = {}
            for scheme, url in raw_proxy.items():
                # 'no_proxy' entries are not proxy URLs — skip them
                if scheme == 'no_proxy' or not url:
                    continue
                # Convert requests format {'http': url} to httpx mount format {'http://': transport}
                key = scheme if scheme.endswith('://') else f'{scheme}://'
                mounts[key] = httpx.HTTPTransport(proxy=url)
            if not mounts:
                mounts = None

    return httpx.Client(
        auth=auth,
        verify=verify,
        cert=cert,
        timeout=timeout,
        headers=headers,
        follow_redirects=is_affirmative(config['allow_redirects']),
        mounts=mounts,
        trust_env=trust_env,
    )


def _translate_httpx_error(e: httpx.HTTPError) -> HTTPError:
    if isinstance(e, httpx.HTTPStatusError):
        return HTTPStatusError(str(e), response=e.response, request=e.request)
    if isinstance(e, httpx.TimeoutException):
        return HTTPTimeoutError(str(e), request=e.request)
    if isinstance(e, httpx.ConnectError):
        return HTTPConnectionError(str(e), request=e.request)
    if isinstance(e, httpx.RequestError):
        return HTTPRequestError(str(e), request=e.request)
    return HTTPError(str(e))


class HTTPXResponseAdapter:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes | str]:
        if decode_unicode:
            return self._response.iter_text(chunk_size=chunk_size)
        return self._response.iter_bytes(chunk_size=chunk_size)

    def iter_lines(
        self,
        chunk_size: int | None = None,
        decode_unicode: bool = False,
        delimiter: bytes | str | None = None,
    ) -> Iterator[bytes | str]:
        # httpx.iter_lines() yields str; encode to bytes unless decode_unicode is requested.
        # Note: httpx normalizes \r\n to \n, which differs from requests behavior.
        for line in self._response.iter_lines():
            yield line if decode_unicode else line.encode()

    def raise_for_status(self) -> None:
        try:
            self._response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPStatusError(str(e), response=e.response, request=e.request) from e

    def __enter__(self) -> HTTPXResponseAdapter:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._response.close()


class HTTPXWrapper:
    def __init__(
        self,
        instance: dict,
        init_config: dict,
        remapper: dict | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._client = _build_httpx_client(instance, init_config, remapper, logger)

    def __del__(self) -> None:  # no cov
        try:
            self._client.close()
        except AttributeError:
            pass

    def _request(self, method: str, url: str, **options: Any) -> HTTPXResponseAdapter:
        try:
            return HTTPXResponseAdapter(self._client.request(method, url, **options))
        except httpx.HTTPError as e:
            raise _translate_httpx_error(e) from e
        except httpx.InvalidURL as e:
            # InvalidURL is not a subclass of httpx.HTTPError; catch it separately.
            raise HTTPRequestError(str(e)) from e

    def get(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("GET", url, **options)

    def post(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("POST", url, **options)

    def head(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("HEAD", url, **options)

    def put(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("PUT", url, **options)

    def patch(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("PATCH", url, **options)

    def delete(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("DELETE", url, **options)

    def options_method(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("OPTIONS", url, **options)
