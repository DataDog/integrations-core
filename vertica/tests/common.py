# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 5433
ID = 'datadog'

CONFIG = {
    'db': ID,
    'server': HOST,
    'port': PORT,
    'username': 'dbadmin',
    'password': 'monitor',
    'timeout': 10,
    'tags': ['foo:bar'],
    'tls_verify': False,
}

# TLS certs
CERTIFICATE_DIR = os.path.join(os.path.dirname(__file__), 'certificate')
cert = os.path.join(CERTIFICATE_DIR, 'cert.cert')
private_key = os.path.join(CERTIFICATE_DIR, 'server.pem')

TLS_CONFIG = {
    'db': 'abc',
    'server': 'localhost',
    'port': '999',
    'username': 'dbadmin',
    'password': 'monitor',
    'timeout': 10,
    'tags': ['foo:bar'],
    'use_tls': True,
    'tls_validate_hostname': True,
    'tls_cert': cert,
    'tls_private_key': private_key,
    'tls_ca_cert': CERTIFICATE_DIR,
}

# Legacy TLS using old config values
TLS_CONFIG_LEGACY = {
    'db': 'abc',
    'server': 'localhost',
    'port': '999',
    'username': 'dbadmin',
    'password': 'monitor',
    'timeout': 10,
    'tags': ['foo:bar'],
    'tls_verify': True,  # old `tls_verify` is now `use_tls`
    'validate_hostname': True,
    'cert': cert,
    'private_key': private_key,
    'ca_cert': CERTIFICATE_DIR,
}


def compose_file(vertica_version):
    major_version = int(vertica_version.split('.', 1)[0])

    if major_version < 10:
        fname = 'docker-compose-9.yaml'
    else:
        fname = 'docker-compose.yaml'

    return os.path.join(HERE, 'docker', fname)
