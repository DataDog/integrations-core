# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()

CONTAINER_NAME = "dd-test-nagios"

INSTANCE_INTEGRATION = {
    'nagios_conf': '/etc/nagios4/nagios.cfg',
    'collect_host_performance_data': True,
    'collect_service_performance_data': False,
}

E2E_METADATA = {
    'start_commands': [
        'apt-get update',
        'DEBIAN_FRONTEND=noninteractive apt-get install exim4-config',
        'apt-get install nagios4-core -yq',
        # Configure nagios
        "sed -i 's/process_performance_data=0/process_performance_data=1/' /etc/nagios4/nagios.cfg",  # Enable perf data
        "sed -i 's/#host_perfdata_file=/host_perfdata_file=/' /etc/nagios4/nagios.cfg",  # Uncomment host_perfdata_file
        "sed -i 's/#host_perfdata_file_template=/host_perfdata_file_template=/' /etc/nagios4/nagios.cfg",
        'service nagios4 start'
    ]
}

EXPECTED_METRICS = ["rta", "pl"]

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
