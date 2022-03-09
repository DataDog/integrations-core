# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

HERE = os.path.dirname(os.path.abspath(__file__))

E2E_METADATA = {
    'use_jmx': True,
    'docker_volumes': [
        '{}/setup/odbc/odbc.ini:/opt/datadog-agent/embedded/etc/odbc.ini'.format(HERE),
        '{}/setup/odbc/odbcinst.ini:/opt/datadog-agent/embedded/etc/odbcinst.ini'.format(HERE),
        '{}/setup/start_commands.sh:/tmp/start_commands.sh'.format(HERE),
    ],
    'env_vars': {'CLASSPATH': '/terajdbc4.jar'},
    'start_commands': ['bash /tmp/start_commands.sh'],
}
