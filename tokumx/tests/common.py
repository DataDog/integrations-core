# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
PORT = '37017'
TOKUMX_SERVER = 'mongodb://{}:{}'.format(HOST, PORT)

INSTANCE = {
    'server': TOKUMX_SERVER,
    'tags': ["optional:tag1"]
}
