# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname, get_here

HOST = get_docker_hostname()
PORT = os.getenv('POWERDNS_HOST_PORT_0', 8082)
HERE = get_here()

POWERDNS_RECURSOR_VERSION = os.environ['POWERDNS_RECURSOR_VERSION']

CONFIG = {"host": HOST, "port": PORT, "api_key": "pdns_api_key"}

CONFIG_V4 = {"host": HOST, "port": PORT, "version": 4, "api_key": "pdns_api_key"}

BAD_CONFIG = {"host": HOST, "port": PORT, "api_key": "nope"}

BAD_API_KEY_CONFIG = {"host": HOST, "port": '1111', "api_key": "pdns_api_key"}


def _config_sc_tags(config):
    host_tag = "recursor_host:{0}".format(config['host'])
    port_tag = "recursor_port:{0}".format(config['port'])
    return [host_tag, port_tag]


def _get_pdns_version():
    return int(POWERDNS_RECURSOR_VERSION[0])
