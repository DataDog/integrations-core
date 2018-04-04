# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

HOST = os.getenv('DOCKER_HOSTNAME', '127.0.0.1')
PORT = os.getenv('POWERDNS_HOST_PORT_0', 8082)
HERE = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    "host": HOST,
    "port": PORT,
    "api_key": "pdns_api_key"
}

CONFIG_V4 = {
    "host": HOST,
    "port": PORT,
    "version": 4,
    "api_key": "pdns_api_key"
}

BAD_CONFIG = {
    "host": HOST,
    "port": PORT,
    "api_key": "nope"
}

BAD_API_KEY_CONFIG = {
    "host": HOST,
    "port": '1111',
    "api_key": "pdns_api_key"
}

def _config_sc_tags(config):
    host_tag = "recursor_host:{0}".format(config['host'])
    port_tag = "recursor_port:{0}".format(config['port'])
    return [host_tag, port_tag]
