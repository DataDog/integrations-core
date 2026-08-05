# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from tuf.ngclient.urllib3_fetcher import Urllib3Fetcher

REQUESTS_CA_BUNDLE_ENVIRONMENT_VARIABLES = ('REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE')


def create_tuf_fetcher(socket_timeout: int = 30) -> Urllib3Fetcher:
    """Create a TUF fetcher that preserves Requests CA bundle configuration."""
    fetcher = Urllib3Fetcher(socket_timeout=socket_timeout)
    for variable in REQUESTS_CA_BUNDLE_ENVIRONMENT_VARIABLES:
        ca_bundle = os.environ.get(variable)
        if ca_bundle:
            option = 'ca_cert_dir' if os.path.isdir(ca_bundle) else 'ca_certs'
            fetcher._proxy_env._kw_args[option] = ca_bundle
            break

    return fetcher
