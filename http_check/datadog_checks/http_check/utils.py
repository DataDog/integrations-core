# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys
from functools import cache
from urllib.parse import unquote, urlparse

import socks

from datadog_checks.base.utils.platform import Platform

EMBEDDED_DIR = 'embedded'

if Platform.is_windows():
    EMBEDDED_DIR += str(sys.version_info[0])


def get_ca_certs_path():
    """
    Get a path to the trusted certificates of the system
    """
    for f in _get_ca_certs_paths():
        if os.path.exists(f):
            return f
    return None


def _get_ca_certs_paths():
    """
    Get a list of possible paths containing certificates

    Check is installed via pip to:
     * Windows: embedded/lib/site-packages/datadog_checks/http_check
     * Linux: embedded/lib/python2.7/site-packages/datadog_checks/http_check

    Certificate is installed to:
     * embedded/ssl/certs/cacert.pem

    walk up to `embedded`, and back down to ssl/certs to find the certificate file
    """
    ca_certs = []

    embedded_root = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.basename(embedded_root) == EMBEDDED_DIR:
            ca_certs.append(os.path.join(embedded_root, 'ssl', 'certs', 'cacert.pem'))
            break
        embedded_root = os.path.dirname(embedded_root)
    else:
        raise OSError(
            'Unable to locate `embedded` directory. Please specify ca_certs in your http yaml configuration file.'
        )

    try:
        import tornado
    except ImportError:
        # if `tornado` is not present, simply ignore its certificates
        pass
    else:
        ca_certs.append(os.path.join(os.path.dirname(tornado.__file__), 'ca-certificates.crt'))

    ca_certs.append('/etc/ssl/certs/ca-certificates.crt')

    return ca_certs


@cache
def parse_proxy_url(url: str) -> dict:
    """
    parse_proxy_url takes an url string and returns a dictionary of proxy parameters
    The tuple is of the form (proxy_type, hostname, port, rdns, username, password)
    The dictionary corresponds exactly to the named parameters expected by socks.set_proxy()
    If no port is specified, the default port for the proxy type will be used (SOCKS:1080, HTTP:8080).

    >>> parse_proxy_url("socks5://user:password@host:123")
    {'proxy_type': 2, 'addr': 'host', 'port': 123, 'rdns': False, 'username': 'user', 'password': 'password'}
    >>> parse_proxy_url("socks5h://host:123")
    {'proxy_type': 2, 'addr': 'host', 'port': 123, 'rdns': True, 'username': None, 'password': None}
    """
    remote_dns = False
    parsed = urlparse(url)

    if parsed.scheme in ['socks5', 'socks5a', 'socks5h']:
        proxy_type = socks.SOCKS5
        remote_dns = parsed.scheme == 'socks5h'
        default_port = 1080
    elif parsed.scheme == 'socks4':
        proxy_type = socks.SOCKS4
        default_port = 1080
    elif parsed.scheme == 'http':
        proxy_type = socks.HTTP
        remote_dns = True
        default_port = 8080
    else:
        raise ValueError(f'unsupported proxy scheme: {url}')

    if not parsed.hostname:
        raise ValueError(f'Empty host component for proxy: {url}')

    try:
        port = parsed.port if parsed.port else default_port
    except Exception as e:
        raise ValueError(f'Invalid port component for proxy {url}, {e}')

    username = unquote(parsed.username, errors='replace') if parsed.username else None
    password = unquote(parsed.password, errors='replace') if parsed.password else None

    return {
        "proxy_type": proxy_type,
        "addr": parsed.hostname,
        "port": port,
        "rdns": remote_dns,
        "username": username,
        "password": password,
    }
