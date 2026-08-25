# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import ssl
from collections.abc import Mapping
from typing import Any

import requests

from datadog_checks.base.config import is_affirmative
from datadog_checks.base.utils import _http_utils

from .http_protocol import HTTPClient
from .tls import create_ssl_context


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
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Include the managed SSL context in requests' connection-pool key."""
        host_params, _ = super().build_connection_pool_key_attributes(request, verify, cert)
        return host_params, {'ssl_context': self.ssl_context}


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


def apply_tls(client: HTTPClient, session: requests.Session) -> None:
    """Apply an HTTP client's TLS behavior to a requests session."""
    use_host_header = (
        is_affirmative(client.tls_config.get('tls_use_host_header')) and client.get_header('Host') is not None
    )
    session.mount(
        'https://',
        create_https_adapter(client.tls_config, use_host_header=use_host_header),
    )
