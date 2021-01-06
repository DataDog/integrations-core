# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ssl


def make_insecure_ssl_client_context():
    """Creates an insecure ssl context for integration that requires to use TLS without checking
    the host authenticity.

    :rtype ssl.Context
    """
    context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
    context.verify_mode = ssl.CERT_NONE
    return context
