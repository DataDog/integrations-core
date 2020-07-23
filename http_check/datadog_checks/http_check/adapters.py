# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ssl
import warnings

import urllib3
from requests.adapters import HTTPAdapter
from urllib3.exceptions import SecurityWarning
from urllib3.packages.ssl_match_hostname import match_hostname
from urllib3.util import ssl_


class WeakCiphersHTTPSConnection(urllib3.connection.VerifiedHTTPSConnection):

    SUPPORTED_CIPHERS = (
        'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:'
        'ECDH+HIGH:DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:'
        'RSA+3DES:ECDH+RC4:DH+RC4:RSA+RC4:!aNULL:!eNULL:!EXP:-MD5:RSA+RC4+MD5'
    )

    def __init__(self, host, port, ciphers=None, **kwargs):
        self.ciphers = ciphers if ciphers is not None else self.SUPPORTED_CIPHERS
        super(WeakCiphersHTTPSConnection, self).__init__(host, port, **kwargs)

    def connect(self):
        # Add certificate verification
        conn = self._new_conn()

        resolved_cert_reqs = ssl_.resolve_cert_reqs(self.cert_reqs)
        resolved_ssl_version = ssl_.resolve_ssl_version(self.ssl_version)

        hostname = self.host
        if getattr(self, '_tunnel_host', None):
            # _tunnel_host was added in Python 2.6.3
            # (See:
            # http://hg.python.org/cpython/rev/0f57b30a152f)
            #
            # However this check is still necessary in 2.7.x

            self.sock = conn
            # Calls self._set_hostport(), so self.host is
            # self._tunnel_host below.
            self._tunnel()
            # Mark this connection as not reusable
            self.auto_open = 0

            # Override the host with the one we're requesting data from.
            hostname = self._tunnel_host

        # Wrap socket using verification with the root certs in trusted_root_certs
        self.sock = ssl_.ssl_wrap_socket(
            conn,
            self.key_file,
            self.cert_file,
            cert_reqs=resolved_cert_reqs,
            ca_certs=self.ca_certs,
            server_hostname=hostname,
            ssl_version=resolved_ssl_version,
            ciphers=self.ciphers,
        )

        if self.assert_fingerprint:
            ssl_.assert_fingerprint(self.sock.getpeercert(binary_form=True), self.assert_fingerprint)
        elif resolved_cert_reqs != ssl.CERT_NONE and self.assert_hostname is not False:
            cert = self.sock.getpeercert()
            if not cert.get('subjectAltName', ()):
                warnings.warn(
                    (
                        'Certificate has no `subjectAltName`, falling back to check for a `commonName` for now. '
                        'This feature is being removed by major browsers and deprecated by RFC 2818. '
                        '(See https://github.com/shazow/urllib3/issues/497 for details.)'
                    ),
                    SecurityWarning,
                )
            match_hostname(cert, self.assert_hostname or hostname)

        self.is_verified = resolved_cert_reqs == ssl.CERT_REQUIRED or self.assert_fingerprint is not None


class WeakCiphersHTTPSConnectionPool(urllib3.connectionpool.HTTPSConnectionPool):

    ConnectionCls = WeakCiphersHTTPSConnection


class WeakCiphersPoolManager(urllib3.poolmanager.PoolManager):
    def _new_pool(self, scheme, host, port):
        if scheme == 'https':
            return WeakCiphersHTTPSConnectionPool(host, port, **(self.connection_pool_kw))
        return super(WeakCiphersPoolManager, self)._new_pool(scheme, host, port)


class WeakCiphersAdapter(HTTPAdapter):
    """"Transport adapter" that allows us to use TLS_RSA_WITH_RC4_128_MD5."""

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        # Rewrite of the
        # requests.adapters.HTTPAdapter.init_poolmanager method
        # to use WeakCiphersPoolManager instead of
        # urllib3's PoolManager
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block

        self.poolmanager = WeakCiphersPoolManager(
            num_pools=connections, maxsize=maxsize, block=block, strict=True, **pool_kwargs
        )
