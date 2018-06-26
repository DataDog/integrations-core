# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))

CHECK_NAME = 'nagios'
CUSTOM_TAGS = ['optional:tag1']

NAGIOS_TEST_LOG = os.path.join(HERE, 'fixtures', 'nagios.log')
NAGIOS_TEST_HOST = os.path.join(HERE, 'fixtures', 'host-perfdata')
NAGIOS_TEST_SVC = os.path.join(HERE, 'fixtures', 'service-perfdata')

NAGIOS_TEST_HOST_TEMPLATE = "[HOSTPERFDATA]\t$TIMET$\t$HOSTNAME$\t$HOSTEXECUTIONTIME$\t$HOSTOUTPUT$\t$HOSTPERFDATA$"
NAGIOS_TEST_SVC_TEMPLATE = "[SERVICEPERFDATA]\t$TIMET$\t$HOSTNAME$\t$SERVICEDESC$\t$SERVICEEXECUTIONTIME$\t"\
                           "$SERVICELATENCY$\t$SERVICEOUTPUT$\t$SERVICEPERFDATA$"
