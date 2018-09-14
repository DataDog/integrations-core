import os
from datadog_checks.utils.common import get_docker_hostname

HOST = get_docker_hostname()
PORT1 = 27017
PORT2 = 27018
MAX_WAIT = 150

MONGODB_SERVER = "mongodb://%s:%s/test" % (HOST, PORT1)
MONGODB_SERVER2 = "mongodb://%s:%s/test" % (HOST, PORT2)


MONGODB_CONFIG = {
    'server': MONGODB_SERVER
}

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
