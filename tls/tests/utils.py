# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import socket
import ssl
import time
from contextlib import contextmanager

from six.moves.urllib.parse import urlparse

from datadog_checks.dev import TempDir
from datadog_checks.tls.utils import closing


@contextmanager
def temp_binary(contents):
    with TempDir() as d:
        path = os.path.join(d, 'temp')

        with open(path, 'wb') as f:
            f.write(contents)

        yield path


@contextmanager
def download_cert(name, host, raw=False):
    host = urlparse(host).hostname or host
    context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    for _ in range(20):
        try:
            with closing(socket.create_connection((host, 443))) as sock:
                with closing(context.wrap_socket(sock, server_hostname=host)) as secure_sock:
                    cert = secure_sock.getpeercert(binary_form=True)
        except Exception:  # no cov
            time.sleep(3)
        else:
            break
    else:  # no cov
        raise Exception('Unable to connect to {}'.format(host))

    with TempDir() as d:
        path = os.path.join(d, name)

        if raw:
            with open(path, 'wb') as f:
                f.write(cert)
        else:
            cert = ssl.DER_cert_to_PEM_cert(cert)
            with open(path, 'w') as f:
                f.write(cert)

        yield path
