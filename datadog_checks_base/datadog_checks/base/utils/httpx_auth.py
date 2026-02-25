# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
httpx.Auth subclasses for Kerberos (GSSAPI) and NTLM authentication.

Both adapters use the `spnego` library, which is the underlying engine
for `requests-kerberos` and `requests-ntlm`. Import is deferred via
lazy_loader so integrations that do not need these auth schemes incur
no startup cost and do not require the optional `spnego` package.
"""

from __future__ import annotations

import base64
import logging
import re
from typing import Generator

import httpx
import lazy_loader

spnego = lazy_loader.load('spnego')

LOGGER = logging.getLogger(__name__)

# Regex to extract a Negotiate/NTLM token from WWW-Authenticate
_NEGOTIATE_RE = re.compile(r'(?:Negotiate|NTLM)\s+([A-Za-z0-9+/=]+)', re.IGNORECASE)


def _extract_token(header_value: str) -> bytes | None:
    """Return the raw token bytes from a Negotiate or NTLM header value."""
    match = _NEGOTIATE_RE.search(header_value or '')
    if match:
        return base64.b64decode(match.group(1))
    return None


class KerberosAuth(httpx.Auth):
    """GSSAPI/Kerberos authentication for httpx, mirroring HTTPKerberosAuth.

    Uses the ``spnego`` library (installed as a dependency of
    ``requests-kerberos``) to perform the Negotiate handshake.

    Parameters
    ----------
    mutual_authentication:
        One of ``'required'`` (default), ``'optional'``, or ``'disabled'``.
    service:
        Kerberos service principal prefix, default ``'HTTP'``.
    delegate:
        Request credential delegation (default: False).
    force_preemptive:
        Send the Negotiate token on the first request without waiting for 401.
    hostname_override:
        Override the hostname used for the service principal name.
    principal:
        Explicit Kerberos principal (``user@REALM``).
    keytab:
        Path to a keytab file. When set, credentials are loaded from the file.
    """

    requires_response_body = False

    def __init__(
        self,
        mutual_authentication: str = 'required',
        service: str = 'HTTP',
        delegate: bool = False,
        force_preemptive: bool = False,
        hostname_override: str | None = None,
        principal: str | None = None,
        keytab: str | None = None,
    ) -> None:
        self._mutual_authentication = mutual_authentication.lower()
        self._service = service
        self._delegate = delegate
        self._force_preemptive = force_preemptive
        self._hostname_override = hostname_override
        self._principal = principal
        self._keytab = keytab

    def _build_context(self, hostname: str) -> object:
        context_req = spnego.ContextReq.sequence_detect
        if self._delegate:
            context_req |= spnego.ContextReq.delegate
        if self._mutual_authentication != 'disabled':
            context_req |= spnego.ContextReq.mutual_auth

        credential = None
        if self._keytab:
            credential = spnego.KerberosKeytab(self._keytab, self._principal)
        elif self._principal:
            credential = spnego.Credential(spnego.CredentialCache(self._principal))

        target_host = self._hostname_override if self._hostname_override is not None else hostname

        return spnego.client(
            username=None if credential else self._principal,
            hostname=target_host,
            service=self._service,
            context_req=context_req,
            protocol='kerberos',
            credential=credential,
        )

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        hostname = request.url.host
        ctx = None

        if self._force_preemptive:
            ctx = self._build_context(hostname)
            token = ctx.step()
            request.headers['Authorization'] = 'Negotiate {}'.format(base64.b64encode(token).decode())
            response = yield request
        else:
            response = yield request

        if response.status_code == 401:
            www_auth = response.headers.get('www-authenticate', '')
            server_token = _extract_token(www_auth)

            ctx = self._build_context(hostname)
            token = ctx.step(in_token=server_token)
            request.headers['Authorization'] = 'Negotiate {}'.format(base64.b64encode(token).decode())
            response = yield request

        # Mutual authentication verification
        if ctx is not None and self._mutual_authentication == 'required':
            www_auth = response.headers.get('www-authenticate', '')
            server_token = _extract_token(www_auth)
            if server_token:
                try:
                    ctx.step(in_token=server_token)
                except Exception:
                    LOGGER.warning('Kerberos mutual authentication failed for %s', hostname)


class NTLMAuth(httpx.Auth):
    """NTLM authentication for httpx using the ``spnego`` library.

    Implements the three-step NTLM handshake:
    1. Type 1 Negotiate → server 401 with Type 2 Challenge
    2. Type 3 Authenticate → authenticated response

    Parameters
    ----------
    username:
        Username in ``DOMAIN\\\\username`` format.
    password:
        Plain-text password.
    """

    requires_response_body = False

    def __init__(self, username: str | None, password: str | None) -> None:
        self._username = username
        self._password = password

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        ntlm_options = spnego.NegotiateOptions.none
        if self._username and self._password:
            # Force pure NTLM (no SSPI/Kerberos fallback) when credentials supplied
            ntlm_options = spnego.NegotiateOptions.use_ntlm

        ctx = spnego.client(
            username=self._username,
            password=self._password,
            protocol='ntlm',
            options=ntlm_options,
        )

        # --- Step 1: Type 1 Negotiate ---
        token1 = ctx.step()
        request.headers['Authorization'] = 'NTLM {}'.format(base64.b64encode(token1).decode())
        response = yield request

        if response.status_code != 401:
            return

        # --- Step 2: Extract Type 2 Challenge and build Type 3 Authenticate ---
        www_auth = response.headers.get('www-authenticate', '')
        challenge = _extract_token(www_auth)
        if not challenge:
            LOGGER.warning('NTLMAuth: no NTLM challenge in 401 response')
            return

        token3 = ctx.step(in_token=challenge)
        request.headers['Authorization'] = 'NTLM {}'.format(base64.b64encode(token3).decode())
        yield request
