# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import copy
import logging
import pymqi
import re

from six.moves import range

from datadog_checks.dev import docker_run
from datadog_checks.ibm_mq import IbmMqCheck

from . import common

log = logging.getLogger(__file__)


@pytest.fixture
def check():
    return IbmMqCheck('ibm_mq', {}, {})


@pytest.fixture
def instance():
    inst = copy.deepcopy(common.INSTANCE)
    return inst


@pytest.fixture
def instance_pattern():
    inst = copy.deepcopy(common.INSTANCE_PATTERN)
    return inst


@pytest.fixture
def instance_collect_all():
    inst = copy.deepcopy(common.INSTANCE_COLLECT_ALL)
    return inst


@pytest.fixture
def instance_queue_regex_tag():
    inst = copy.deepcopy(common.INSTANCE_QUEUE_REGEX_TAG)
    return inst


@pytest.fixture
def seed_data():
    publish()
    consume()


def publish():
    conn_info = "%s(%s)" % (common.HOST, common.PORT)

    qmgr = pymqi.connect(common.QUEUE_MANAGER, common.CHANNEL, conn_info, common.USERNAME, common.PASSWORD)

    queue = pymqi.Queue(qmgr, common.QUEUE)

    for i in range(10):
        try:
            message = 'Hello from Python! Message {}'.format(i)
            log.info("sending message: {}".format(message))
            queue.put(message.encode())
        except Exception as e:
            log.info("exception publishing: {}".format(e))
            queue.close()
            qmgr.disconnect()
            return

    queue.close()
    qmgr.disconnect()


def consume():
    conn_info = "%s(%s)" % (common.HOST, common.PORT)

    qmgr = pymqi.connect(common.QUEUE_MANAGER, common.CHANNEL, conn_info, common.USERNAME, common.PASSWORD)

    queue = pymqi.Queue(qmgr, common.QUEUE)

    for _ in range(10):
        try:
            message = queue.get()
            print("got a new message: {}".format(message))
        except Exception as e:
            if not re.search("MQRC_NO_MSG_AVAILABLE", e.errorAsString()):
                print(e)
                queue.close()
                qmgr.disconnect()
                return
            else:
                pass

    queue.close()
    qmgr.disconnect()


@pytest.fixture(scope='session')
def dd_environment():

    if common.MQ_VERSION == '9':
        log_pattern = "AMQ5026I: The listener 'DEV.LISTENER.TCP' has started. ProcessId"
    elif common.MQ_VERSION == '8':
        log_pattern = r".*QMNAME\(datadog\)\s*STATUS\(Running\).*"

    env = {
        'COMPOSE_DIR': common.COMPOSE_DIR,
    }

    with docker_run(
        common.COMPOSE_FILE_PATH,
        env_vars=env,
        log_patterns=log_pattern,
        sleep=10
    ):
        yield common.INSTANCE
