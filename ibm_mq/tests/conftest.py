# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging
import os
import re

import pytest
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor
from pymqi import ensure_bytes
from six.moves import range

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


@pytest.fixture(scope='session')
def dd_environment():

    if common.MQ_VERSION == '9':
        log_pattern = "AMQ5026I: The listener 'DEV.LISTENER.TCP' has started. ProcessId"
    elif common.MQ_VERSION == '8':
        log_pattern = r".*QMNAME\({}\)\s*STATUS\(Running\).*".format(common.QUEUE_MANAGER)
    else:
        raise RuntimeError('Invalid version: {}'.format(common.MQ_VERSION))

    e2e_meta = copy.deepcopy(common.E2E_METADATA)
    e2e_meta.setdefault('docker_volumes', [])
    e2e_meta['docker_volumes'].append("{}:/opt/pki/keys".format(os.path.join(common.HERE, 'keys')))

    with docker_run(
        common.COMPOSE_FILE_PATH, conditions=[
            CheckDockerLogs('ibm_mq1', log_pattern),
            WaitFor(prepare_queue_manager, attempts=5)
        ], sleep=10,
    ):
        yield common.INSTANCE_SSL, e2e_meta


def prepare_queue_manager():
    # Late import to not require it for e2e
    import pymqi

    conn_info = '{0}({1})'.format(common.HOST, common.PORT)

    qmgr = pymqi.QueueManager(None)
    qmgr.connectTCPClient(common.QUEUE_MANAGER, pymqi.CD(), common.CHANNEL,
        conn_info, common.USERNAME, common.PASSWORD)
    pcf = pymqi.PCFExecute(qmgr, response_wait_interval=5000)

    attrs = [
        pymqi.CFST(Parameter=pymqi.CMQC.MQCA_SSL_KEY_REPOSITORY, String=b'/etc/mqm/pki/keys/qm1'),
        pymqi.CFST(Parameter=pymqi.CMQC.MQCA_CERT_LABEL, String=b'qm1')
    ]
    pcf.MQCMD_CHANGE_Q_MGR(attrs)

    tls_channel_name = ensure_bytes(common.CHANNEL_SSL)
    cypher_spec = b'TLS_RSA_WITH_AES_256_CBC_SHA256'
    client_dn = b'CN=client'
    certificate_label_qmgr = b'qm1'

    attrs = []
    attrs.append(pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_CHANNEL_NAME,
                            String=ensure_bytes(tls_channel_name)))
    attrs.append(pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACH_CHANNEL_TYPE,
                            Value=pymqi.CMQC.MQCHT_SVRCONN))
    attrs.append(pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_SSL_CIPHER_SPEC,
                            String=cypher_spec))
    attrs.append(pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_SSL_PEER_NAME,
                            String=client_dn))
    attrs.append(pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACH_SSL_CLIENT_AUTH,
                            Value=pymqi.CMQXC.MQSCA_OPTIONAL))
    attrs.append(pymqi.CFST(Parameter=pymqi.CMQC.MQCA_CERT_LABEL,
                            String=certificate_label_qmgr))
    attrs.append(pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACF_REPLACE,
                            Value=pymqi.CMQCFC.MQRP_YES))
    res = create_channel(pcf, tls_channel_name, attrs)
    print("res", res)

    attrs = []
    attrs.append(pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_CHANNEL_NAME,
                            String=ensure_bytes(tls_channel_name)))
    attrs.append(pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACF_CHLAUTH_TYPE,
                            Value=pymqi.CMQCFC.MQCAUT_USERMAP))
    attrs.append(pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACF_ACTION,
                            Value=pymqi.CMQCFC.MQACT_REPLACE))
    attrs.append(pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_CLIENT_USER_ID,
                            String=ensure_bytes(common.USERNAME)))
    attrs.append(pymqi.CFIN(Parameter=pymqi.CMQC.MQIA_CHECK_CLIENT_BINDING,
                            Value=pymqi.CMQCFC.MQCHK_REQUIRED_ADMIN))
    attrs.append(pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACH_USER_SOURCE,
                            Value=pymqi.CMQC.MQUSRC_MAP))
    attrs.append(pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_MCA_USER_ID,
                            String=b'mqm'))

    res = pcf.MQCMD_SET_CHLAUTH_REC(attrs)
    print("res", res)

    attrs = []
    attrs.append(pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_CHANNEL_NAME,
                            String=ensure_bytes(tls_channel_name)))
    attrs.append(pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACF_CHLAUTH_TYPE,
                            Value=pymqi.CMQCFC.MQCAUT_BLOCKUSER))
    attrs.append(pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_MCA_USER_ID_LIST,
                            String=b'nobody'))
    attrs.append(pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACH_WARNING,
                            Value=pymqi.CMQC.MQWARN_NO))
    attrs.append(pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACF_ACTION,
                            Value=pymqi.CMQCFC.MQACT_REPLACE))

    res = pcf.MQCMD_SET_CHLAUTH_REC(attrs)
    print("res", res)


def create_channel(pcf, channel_name, attrs=None):
    import pymqi

    if not attrs:
        attrs = []
        attrs.append(pymqi.CFST(Parameter=pymqi.CMQCFC.MQCACH_CHANNEL_NAME,
                                String=ensure_bytes(channel_name)))
        attrs.append(pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACH_CHANNEL_TYPE,
                                Value=pymqi.CMQC.MQCHT_SVRCONN))
        attrs.append(pymqi.CFIN(Parameter=pymqi.CMQCFC.MQIACF_REPLACE,
                                Value=pymqi.CMQCFC.MQRP_YES))
    return pcf.MQCMD_CREATE_CHANNEL(attrs)
