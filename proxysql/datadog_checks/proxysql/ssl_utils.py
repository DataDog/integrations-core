# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import ssl

from datadog_checks.base import ConfigurationError


def make_insecure_ssl_client_context():
    """Creates an insecure ssl context for integration that requires to use TLS without checking
    the host authenticity.

    :rtype ssl.Context
    """
    context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
    context.verify_mode = ssl.CERT_NONE
    return context


def make_secure_ssl_client_context(
    ca_cert=None, client_cert=None, client_key=None, check_hostname=True, protocol=ssl.PROTOCOL_TLS,
):
    """Creates a secure ssl context for integration that requires one.
    :param str ca_cert:     Path to a file of concatenated CA certificates in PEM format or to a directory containing
                            several CA certificates in PEM format
    :param str client_cert: Path to a single file in PEM format containing the certificate as well as any number of
                            CA certificates needed to establish the certificate's authenticity.
    :param str client_key:  Must point to a file containing the private key. Otherwise the private key will be taken
                            from certfile as well.
    :param bool check_hostname: Whether to match the peer cert's hostname
    :param int protocol:    Client side protocol (should be one of the `ssl.PROTOCOL_*` constants)
                            By default selects the highest protocol version possible.

    :rtype ssl.Context
    """
    # https://docs.python.org/3/library/ssl.html#ssl.SSLContext
    # https://docs.python.org/3/library/ssl.html#ssl.PROTOCOL_TLS
    context = ssl.SSLContext(protocol=protocol)

    # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.verify_mode
    context.verify_mode = ssl.CERT_REQUIRED

    # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.check_hostname
    context.check_hostname = check_hostname

    ca_file, ca_path = None, None
    if os.path.isdir(ca_cert):
        ca_path = ca_cert
    elif os.path.isfile(ca_cert):
        ca_file = ca_cert
    else:
        raise ConfigurationError("Specified tls_ca_cert: {} should be a valid file or directory.".format(ca_cert))

    # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_verify_locations
    if ca_file or ca_path:
        context.load_verify_locations(ca_file, ca_path, None)

    # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_default_certs
    else:
        context.load_default_certs(ssl.Purpose.SERVER_AUTH)

    # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_cert_chain
    if client_cert:
        # If client_key is not defined, load_cert_chain reads the key from the client_cert
        context.load_cert_chain(client_cert, keyfile=client_key)

    return context
