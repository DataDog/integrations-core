# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.sap_hana import SapHanaCheck

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
SERVER = get_docker_hostname()
PORT = 39017
TIMEOUT = 20
CONFIG = {'server': SERVER, 'port': PORT, 'username': 'datadog', 'password': 'Datadog9000', 'timeout': TIMEOUT}
ADMIN_CONFIG = {'server': SERVER, 'port': PORT, 'username': 'system', 'password': 'Admin1337'}

# Name the test harness reports to HANA, recorded in AUDIT_LOG.APPLICATION_NAME for the statements
# it audits. Set explicitly because hdbcli otherwise defaults APPLICATION to the client's process
# name, which is not stable across CI runs: the hatch environment's interpreter has been invoked as
# both `python3` and `python` depending on the uv version, silently changing the audited value.
AUDIT_APPLICATION_NAME = 'datadog-test-harness'

E2E_METADATA = {'start_commands': ['pip install hdbcli==2.21.28']}

CAN_CONNECT_SERVICE_CHECK = 'sap_hana.{}'.format(SapHanaCheck.SERVICE_CHECK_CONNECT)


def connection_flaked(aggregator):
    # HANA connection some times flakes, in that case the check will reconnect on next run
    # And a warning service check will be emitted
    service_checks = aggregator.service_checks(CAN_CONNECT_SERVICE_CHECK)
    all_ok = all(service_check.status == SapHanaCheck.OK for service_check in service_checks)
    return not all_ok
