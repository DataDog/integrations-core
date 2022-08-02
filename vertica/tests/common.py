# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.vertica.utils import parse_major_version

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

VERTICA_MAJOR_VERSION = parse_major_version(os.environ.get('VERTICA_VERSION', 9))


def connection_options_from_config(config):
    return {
        'database': config['db'],
        'host': config['server'],
        'port': config['port'],
        'user': config['username'],
        'password': config['password'],
        'connection_timeout': config['timeout'],
        'connection_load_balance': config.get('connection_load_balance'),
    }
