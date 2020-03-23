# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HOST = get_docker_hostname()
PORT1 = 27017
PORT2 = 27018
MAX_WAIT = 150

MONGODB_SERVER = "mongodb://%s:%s/test" % (HOST, PORT1)
MONGODB_VERSION = os.environ['MONGO_VERSION']

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

DEFAULT_INSTANCE = {'server': MONGODB_SERVER}
