# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HOST = get_docker_hostname()
PORT = '8080'

COCKROACHDB_VERSION = os.getenv('COCKROACHDB_VERSION')
