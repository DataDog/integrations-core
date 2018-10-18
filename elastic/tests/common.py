# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
USER = "elastic"
PASSWORD = "changeme"
HOST = get_docker_hostname()
PORT = '9200'
CLUSTER_TAG = ["cluster_name:test-cluster"]
URL = 'http://{}:{}'.format(HOST, PORT)
