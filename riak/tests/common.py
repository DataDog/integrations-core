# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

SERVICE_CHECK_NAME = 'riak.can_connect'

HERE = os.path.dirname(os.path.abspath(__file__))

HOST = get_docker_hostname()
PORT = 18098
BASE_URL = "http://{0}:{1}".format(HOST, PORT)
INSTANCE = {
    "url": "{0}/stats".format(BASE_URL),
    "tags": ["my_tag"]
}
