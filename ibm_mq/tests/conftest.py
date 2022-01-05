# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging
import os
import re

import pytest
from six.moves import range

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor
from datadog_checks.dev.utils import ON_WINDOWS

from . import common

log = logging.getLogger(__file__)


@pytest.fixture(scope='session')
def get_check():
    # Late import to ignore missing library for e2e
    from datadog_checks.ibm_mq import IbmMqCheck

    yield lambda instance: IbmMqCheck('ibm_mq', {}, [instance])


@pytest.fixture
def instance():
    inst = copy.deepcopy(common.INSTANCE)
    return inst


@pytest.fixture
def instance_ssl():
    inst = copy.deepcopy(common.INSTANCE_SSL)
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
def instance_ssl_dummy():
    inst = copy.deepcopy(common.INSTANCE)
    inst['ssl_auth'] = 'yes'
    inst['ssl_cipher_spec'] = 'TLS_RSA_WITH_AES_256_CBC_SHA256'
    inst['ssl_key_repository_location'] = '/dummy'
    return inst


@pytest.fixture
def seed_data():
    publish()
    consume()


def publish():
    # Late import to not require it for e2e
    import pymqi

    conn_info = "%s(%s)" % (common.HOST, common.PORT)

    qmgr = pymqi.connect(common.QUEUE_MANAGER, common.CHANNEL, conn_info, common.USERNAME, common.PASSWORD)

    queue = pymqi.Queue(qmgr, common.QUEUE)

    for i in range(10):
        try:
            message = 'Hello from Python! Message {}'.format(i)
            log.info("sending message: %s", message)
            queue.put(message.encode())
        except Exception as e:
            log.info("exception publishing: %s", e)
            queue.close()
            qmgr.disconnect()
            return

    queue.close()
    qmgr.disconnect()


def consume():
    # Late import to not require it for e2e
    import pymqi

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


def prepare_queue_manager():
    import pymqi

    conn_info = '{0}({1})'.format(common.HOST, common.PORT)
    qm_name = common.QUEUE_MANAGER.lower()

    qmgr = pymqi.QueueManager(None)
    qmgr.connectTCPClient(common.QUEUE_MANAGER, pymqi.CD(), common.CHANNEL, conn_info, common.USERNAME, common.PASSWORD)
    pcf = pymqi.PCFExecute(qmgr, response_wait_interval=5000)

    attrs = [
        pymqi.CFST(
            Parameter=pymqi.CMQC.MQCA_SSL_KEY_REPOSITORY,
            String=pymqi.ensure_bytes('/etc/mqm/pki/keys/{}'.format(qm_name)),
        ),
        pymqi.CFST(Parameter=pymqi.CMQC.MQCA_CERT_LABEL, String=pymqi.ensure_bytes(qm_name)),
    ]
    pcf.MQCMD_CHANGE_Q_MGR(attrs)

    tls_channel_name = pymqi.ensure_bytes(common.CHANNEL_SSL)
    cypher_spec = pymqi.ensure_bytes(common.SSL_CYPHER_SPEC)
    client_dn = pymqi.ensure_bytes('CN={}'.format(common.SSL_CLIENT_LABEL))
    certificate_label_qmgr = pymqi.ensure_bytes(qm_name)

    attrs = [
        pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_CHANNEL_NAME, String=pymqi.ensure_bytes(tls_channel_name)),
        pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACH_CHANNEL_TYPE, Value=pymqi.CMQC.MQCHT_SVRCONN),
        pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_SSL_CIPHER_SPEC, String=cypher_spec),
        pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_SSL_PEER_NAME, String=client_dn),
        pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACH_SSL_CLIENT_AUTH, Value=pymqi.CMQXC.MQSCA_OPTIONAL),
        pymqi.CFST(Parameter=pymqi.CMQC.MQCA_CERT_LABEL, String=certificate_label_qmgr),
        pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACF_REPLACE, Value=pymqi.CMQCFC.MQRP_YES),
    ]
    pcf.MQCMD_CREATE_CHANNEL(attrs)

    attrs = [
        pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_CHANNEL_NAME, String=pymqi.ensure_bytes(tls_channel_name)),
        pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACF_CHLAUTH_TYPE, Value=pymqi.CMQCFC.MQCAUT_USERMAP),
        pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACF_ACTION, Value=pymqi.CMQCFC.MQACT_REPLACE),
        pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_CLIENT_USER_ID, String=pymqi.ensure_bytes(common.USERNAME)),
        pymqi.CFIN(Parameter=pymqi.CMQC.MQIA_CHECK_CLIENT_BINDING, Value=pymqi.CMQCFC.MQCHK_REQUIRED_ADMIN),
        pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACH_USER_SOURCE, Value=pymqi.CMQC.MQUSRC_MAP),
        pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_MCA_USER_ID, String=b'mqm'),
    ]
    pcf.MQCMD_SET_CHLAUTH_REC(attrs)

    attrs = [
        pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_CHANNEL_NAME, String=pymqi.ensure_bytes(tls_channel_name)),
        pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACF_CHLAUTH_TYPE, Value=pymqi.CMQCFC.MQCAUT_BLOCKUSER),
        pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_MCA_USER_ID_LIST, String=b'nobody'),
        pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACH_WARNING, Value=pymqi.CMQC.MQWARN_NO),
        pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACF_ACTION, Value=pymqi.CMQCFC.MQACT_REPLACE),
    ]
    pcf.MQCMD_SET_CHLAUTH_REC(attrs)

    pcf.disconnect()
    qmgr.disconnect()


@pytest.fixture(scope='session')
def dd_environment():

    if common.MQ_VERSION == 9:
        log_pattern = "AMQ5026I: The listener 'DEV.LISTENER.TCP' has started. ProcessId"
    elif common.MQ_VERSION == 8:
        log_pattern = r".*QMNAME\({}\)\s*STATUS\(Running\).*".format(common.QUEUE_MANAGER)
    else:
        raise RuntimeError('Invalid version: {}'.format(common.MQ_VERSION))

    e2e_meta = copy.deepcopy(common.E2E_METADATA)
    e2e_meta.setdefault('docker_volumes', [])
    e2e_meta['docker_volumes'].append("{}:/opt/pki/keys".format(os.path.join(common.HERE, 'keys')))

    conditions = [CheckDockerLogs('ibm_mq1', log_pattern)]
    if not ON_WINDOWS:
        conditions.append(WaitFor(prepare_queue_manager))

    with docker_run(compose_file=common.COMPOSE_FILE_PATH, build=True, conditions=conditions, sleep=10, attempts=2):
        yield common.INSTANCE, e2e_meta
