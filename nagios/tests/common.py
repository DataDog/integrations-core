# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()

CONTAINER_NAME = "dd-test-nagios"
HOST_PERFDATA_FILE = 'host-perfdata.log'
SERVICE_PERFDATA_FILE = 'service-perfdata.log'

INSTANCE_INTEGRATION = {
    'nagios_conf': '/opt/nagios/etc/nagios.cfg',
    'collect_host_performance_data': True,
    'collect_service_performance_data': True,
}

CHECK_NAME = 'nagios'
CUSTOM_TAGS = ['optional:tag1']

NAGIOS_TEST_LOG = os.path.join(HERE, 'fixtures', 'nagios')
NAGIOS_TEST_HOST = os.path.join(HERE, 'fixtures', 'host-perfdata')
NAGIOS_TEST_SVC = os.path.join(HERE, 'fixtures', 'service-perfdata')

NAGIOS_TEST_ALT_HOST_TEMPLATE = "[HOSTPERFDATA]\t$TIMET$\t$HOSTNAME$\t$HOSTEXECUTIONTIME$\t$HOSTOUTPUT$\t$HOSTPERFDATA$"
NAGIOS_TEST_ALT_SVC_TEMPLATE = (
    "[SERVICEPERFDATA]\t$TIMET$\t$HOSTNAME$\t$SERVICEDESC$\t$SERVICEEXECUTIONTIME$\t"
    "$SERVICELATENCY$\t$SERVICEOUTPUT$\t$SERVICEPERFDATA$"
)

NAGIOS_TEST_SVC_TEMPLATE = (
    "DATATYPE::SERVICEPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\t"
    "SERVICEDESC::$SERVICEDESC$\tSERVICEPERFDATA::$SERVICEPERFDATA$\t"
    "SERVICECHECKCOMMAND::$SERVICECHECKCOMMAND$\tHOSTSTATE::$HOSTSTATE$\t"
    "HOSTSTATETYPE::$HOSTSTATETYPE$\tSERVICESTATE::$SERVICESTATE$\t"
    "SERVICESTATETYPE::$SERVICESTATETYPE$"
)

NAGIOS_TEST_HOST_TEMPLATE = (
    "DATATYPE::HOSTPERFDATA\tTIMET::$TIMET$\tHOSTNAME::$HOSTNAME$\t"
    "HOSTPERFDATA::$HOSTPERFDATA$\tHOSTCHECKCOMMAND::$HOSTCHECKCOMMAND$\t"
    "HOSTSTATE::$HOSTSTATE$\tHOSTSTATETYPE::$HOSTSTATETYPE$"
)
