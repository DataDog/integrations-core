# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging
import re
import time

import pytest
from six.moves import range
from tests.common import MQ_COMPOSE

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.ibm_mq import IbmMqCheck
from datadog_checks.ibm_mq.collectors.utils import CustomPCFExecute

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
def instance_with_connection_name():
    inst = copy.deepcopy(common.INSTANCE_WITH_CONNECTION_NAME)
    return inst


@pytest.fixture
def instance_queue_pattern():
    inst = copy.deepcopy(common.INSTANCE_QUEUE_PATTERN)
    return inst


@pytest.fixture
def instance_queue_regex():
    inst = copy.deepcopy(common.INSTANCE_QUEUE_REGEX)
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


@pytest.fixture
def seed_cluster_data():
    if 'cluster' not in MQ_COMPOSE:
        return
    publish_cluster()
    wait_channel_stats()


def publish():
    import pymqi

    qm = get_queue_manager()

    queue = pymqi.Queue(qm, common.QUEUE)

    for i in range(10):
        try:
            message = 'Hello from Python! Message {}'.format(i)
            log.info("sending message: %s", message)
            queue.put(message.encode())
        except Exception as e:
            log.info("exception publishing: %s", e)
            queue.close()
            qm.disconnect()
            return

    queue.close()
    qm.disconnect()


def consume():
    import pymqi

    queue_manager = get_queue_manager()

    queue = pymqi.Queue(queue_manager, common.QUEUE)

    for _ in range(10):
        try:
            message = queue.get()
            print("got a new message: {}".format(message))
        except Exception as e:
            if not re.search("MQRC_NO_MSG_AVAILABLE", e.errorAsString()):
                print(e)
                queue.close()
                queue_manager.disconnect()
                return
            else:
                pass

    queue.close()
    queue_manager.disconnect()


def publish_cluster():
    import pymqi

    conn_info = "%s(%s)" % (common.HOST, '11415')
    queue_manager = pymqi.connect("QM2", common.CHANNEL, conn_info, common.USERNAME, common.PASSWORD)

    queue = pymqi.Queue(queue_manager, "APP.QUEUE.1")

    for i in range(10):
        try:
            message = 'Hello from Python! Message {}'.format(i)
            log.info("sending message: %s", message)
            queue.put(message.encode())
        except Exception as e:
            log.info("exception publishing: %s", e)
            queue.close()
            queue_manager.disconnect()
            return

    queue.close()
    queue_manager.disconnect()


def get_queue_manager():
    # Late import to not require it for e2e
    import pymqi

    conn_info = "%s(%s)" % (common.HOST, common.PORT)
    queue_manager = pymqi.connect(common.QUEUE_MANAGER, common.CHANNEL, conn_info, common.USERNAME, common.PASSWORD)

    return queue_manager


def wait_channel_stats():
    import pymqi

    queue_manager = get_queue_manager()

    queue_name = 'SYSTEM.ADMIN.STATISTICS.QUEUE'
    queue = pymqi.Queue(queue_manager, queue_name, pymqi.CMQC.MQOO_BROWSE)

    get_opts = pymqi.GMO(
        Options=pymqi.CMQC.MQGMO_NO_SYNCPOINT
        | pymqi.CMQC.MQGMO_FAIL_IF_QUIESCING
        | pymqi.CMQC.MQGMO_BROWSE_NEXT,  # We just browse to avoid consuming the message
        Version=pymqi.CMQC.MQGMO_VERSION_2,
        MatchOptions=pymqi.CMQC.MQMO_MATCH_CORREL_ID,
    )
    get_md = pymqi.MD()

    # Wait for stats (especially channel stat that might take time to be produced)
    for _ in range(100):
        try:
            raw_message = queue.get(None, get_md, get_opts)
            msg, header = CustomPCFExecute.unpack(raw_message)
            if header.Command == pymqi.CMQCFC.MQCMD_STATISTICS_CHANNEL:
                print("Got MQCMD_STATISTICS_CHANNEL")
                break
        except pymqi.MQMIError as err:
            if err.reason == pymqi.CMQC.MQRC_NO_MSG_AVAILABLE:
                time.sleep(1)
                continue
            else:
                raise

    queue.close()
    queue_manager.disconnect()


@pytest.fixture(scope='session')
def dd_environment():

    if common.MQ_VERSION.startswith('9'):
        log_pattern = "AMQ5026I: The listener 'DEV.LISTENER.TCP' has started. ProcessId"
    elif common.MQ_VERSION == '8':
        log_pattern = r".*QMNAME\({}\)\s*STATUS\(Running\).*".format(common.QUEUE_MANAGER)
    else:
        raise RuntimeError('Invalid version: {}'.format(common.MQ_VERSION))

    env = {'COMPOSE_DIR': common.COMPOSE_DIR}

    with docker_run(
        common.COMPOSE_FILE_PATH,
        env_vars=env,
        # conditions=[CheckDockerLogs('ibm_mq1', log_pattern), WaitFor(wait_channel_stats)],
        conditions=[CheckDockerLogs('ibm_mq1', log_pattern)],
        sleep=10,
    ):
        yield common.INSTANCE, common.E2E_METADATA
