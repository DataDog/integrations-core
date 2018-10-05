# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from time import sleep

import pytest
import xmlrpclib

from .common import PROCESSES, STATUSES, SUPERVISORD_CONFIG, BAD_SUPERVISORD_CONFIG, supervisor_check
from datadog_checks.checks.base import AgentCheck
from datadog_checks.dev import docker_run, get_docker_hostname


# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

CHECK_NAME = 'supervisord'
HOST = get_docker_hostname()
PORT = 19001
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://{}:{}".format(HOST, PORT)


@pytest.fixture(scope='session', autouse=True)
def spin_up_supervisord():
    with docker_run(compose_file=os.path.join(HERE, 'compose', 'supervisord.yaml'), endpoints=URL):
        server = xmlrpclib.Server('http://localhost:19001/RPC2')
        server.supervisor.startAllProcesses()
        yield


# Supervisord should run 3 programs for 10, 20 and 30 seconds
# respectively.
# The following dictionnary shows the processes by state for each iteration.
PROCESSES_BY_STATE_BY_ITERATION = map(lambda x: dict(up=PROCESSES[x:], down=PROCESSES[:x], unknown=[]), range(4))


def test_check(aggregator):
    """
    Run Supervisord check and assess coverage
    """
    instance_tags = ["supervisord_server:travis"]

    for i in range(4):
        # Run the check
        supervisor_check.check(SUPERVISORD_CONFIG)

        # Check metrics and service checks scoped by process
        for proc in PROCESSES:
            process_tags = instance_tags + ["supervisord_process:{0}".format(proc)]
            process_status = AgentCheck.OK if proc in PROCESSES_BY_STATE_BY_ITERATION[i]['up'] else AgentCheck.CRITICAL

            aggregator.assert_metric("supervisord.process.uptime", tags=process_tags, count=1)
            aggregator.assert_service_check(
                "supervisord.process.status", status=process_status, tags=process_tags, count=1
            )

        # Check instance metrics
        for status in STATUSES:
            status_tags = instance_tags + ["status:{0}".format(status)]
            count_processes = len(PROCESSES_BY_STATE_BY_ITERATION[i][status])
            aggregator.assert_metric("supervisord.process.count", value=count_processes, tags=status_tags, count=1)

        aggregator.assert_service_check("supervisord.can_connect", status=AgentCheck.OK, tags=instance_tags, count=1)
        aggregator.reset()

        # Sleep 10s to give enough time to processes to terminate
        sleep(10)


def test_connection_falure(aggregator):
    """
    Service check reports connection failure
    """
    config = {'instances': BAD_SUPERVISORD_CONFIG}
    instance_tags = ["supervisord_server:travis"]

    with pytest.raises(Exception):
        supervisor_check.check(config)
        aggregator.assert_service_check(
            "supervisord.can_connect", status=AgentCheck.CRITICAL, tags=instance_tags, count=1
        )
