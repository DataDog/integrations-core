# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()

CONTAINER_NAME = "dd-test-nagios"

INSTANCE_INTEGRATION = {
    'nagios_conf': '/usr/local/nagios/etc/nagios.cfg',
    'collect_host_performance_data': True,
    'collect_task_metrics': True
}

E2E_METADATA = {
    'start_commands': [
        # Install prerequistes
        'apt-get update',
        'apt-get install wget build-essential apache2 php php-gd libgd-dev sendmail unzip libapache2-mod-php7.3 -y',
        # User and group configuration
        'useradd nagios',
        'groupadd nagcmd',
        'usermod -a -G nagcmd nagios',
        'usermod -a -G nagios,nagcmd www-data',
        # Download and extract nagios core
        'wget https://assets.nagios.com/downloads/nagioscore/releases/nagios-4.2.0.tar.gz',
        'tar -xzf nagios*.tar.gz',
        # Compile nagios
        '(cd nagios-4.2.0; ./configure --with-nagios-group=nagios --with-command-group=nagcmd)',
        '(cd nagios-4.2.0; make all)'
        '(cd nagios-4.2.0; make install && make install-commandmode &&  make install-init && make install-config)',
        '(cd nagios-4.2.0; install -c -m 644 sample-config/httpd.conf /etc/apache2/sites-available/nagios.conf)',
        '(cd nagios-4.2.0; cp -R contrib/eventhandlers/ /usr/local/nagios/libexec/)',
        'chown -R nagios:nagios /usr/local/nagios/libexec/eventhandlers',
        # Install the Nagios plugins
        'wget https://nagios-plugins.org/download/nagios-plugins-2.1.2.tar.gz',
        'tar -xzf nagios-plugins*.tar.gz',
        '(cd nagios-plugins-2.1.2/; bash configure --with-nagios-user=nagios --with-nagios-group=nagios --with-openssl)',
        '(cd nagios-plugins-2.1.2/; make && make install)',
        # Configure nagios
        "sed -i 's/#cfg_dir=\/usr\/local\/nagios\/etc\/servers/cfg_dir=\/usr\/local\/nagios\/etc\/servers/' /usr/local/nagios/etc/nagios.cfg"  # Uncomment cfg_dir,
        'mkdir -p /usr/local/nagios/etc/servers',
        # Configure Apache
        # Enable apache modules
        'a2enmod rewrite',
        'a2enmod cgi',
        # Enable nagios virtualhost
        'ln -s /etc/apache2/sites-available/nagios.conf /etc/apache2/sites-enabled/',
        # Restart Apache and Nagios
        'service apache2 restart'
        'service nagios start'
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
