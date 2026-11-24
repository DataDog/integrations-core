# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import hashlib
import os
import socket
import ssl
import time
from contextlib import contextmanager
from urllib.parse import urlparse

from cryptography.x509 import load_pem_x509_certificate

from datadog_checks.dev import TempDir


@contextmanager
def temp_binary(contents):
    with TempDir('binaryjunk') as d:
        path = os.path.join(d, 'temp')

        with open(path, 'wb') as f:
            f.write(contents)

        yield path


def download_cert(filepath, host, raw=False):
    host = urlparse(host).hostname or host
    context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    for _ in range(20):
        try:
            with socket.create_connection((host, 443)) as sock:
                with context.wrap_socket(sock, server_hostname=host) as secure_sock:
                    cert = secure_sock.getpeercert(binary_form=True)
        except Exception:  # no cov
            time.sleep(3)
        else:
            break
    else:  # no cov
        raise Exception('Unable to connect to {}'.format(host))

    if raw:
        with open(filepath, 'wb') as f:
            f.write(cert)
    else:
        cert = ssl.DER_cert_to_PEM_cert(cert)
        with open(filepath, 'w') as f:
            f.write(cert)


def expected_cert_identity_tags(pem_path):
    with open(pem_path) as f:
        pem = f.read()

    der = ssl.PEM_cert_to_DER_cert(pem)
    serial_number = load_pem_x509_certificate(pem.encode()).serial_number
    return [
        'cert_fingerprint_sha256:{}'.format(hashlib.sha256(der).hexdigest()),
        'cert_serial_number:{:x}'.format(serial_number),
    ]
