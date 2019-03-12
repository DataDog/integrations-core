import logging
import requests
import time

from datadog_checks.utils.common import get_docker_hostname
from datadog_checks.dev import get_here

log = logging.getLogger('test_kong')

HERE = get_here()

CHECK_NAME = 'kong'
HOST = get_docker_hostname()
PORT = 8001

STATUS_URL = 'http://{0}:{1}/status/'.format(HOST, PORT)

instance_1 = {
    'kong_status_url': STATUS_URL,
    'tags': ['first_instance']
}

instance_2 = {
    'kong_status_url': STATUS_URL,
    'tags': ['second_instance']
}

CONFIG_STUBS = [instance_1, instance_2]


def wait_for_cluster():
    for _ in range(0, 100):
        res = None
        try:
            res = requests.get(STATUS_URL)
            res.raise_for_status()
            return True
        except Exception as e:
            log.debug("exception: {0} res: {1}".format(e, res))
            time.sleep(2)

    return False
