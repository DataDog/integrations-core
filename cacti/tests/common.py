# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev import get_here, get_docker_hostname

HERE = get_here()
HOST = get_docker_hostname()

# ID
CONTAINER_NAME = "dd-test-cacti"

RRD_PATH = '/var/www/html/cacti/rra'

INSTANCE_INTEGRATION = {
    'mysql_host': HOST,
    'mysql_user': 'cactiuser',
    'mysql_password': 'cactipass',
    'rrd_path': RRD_PATH,
    'collect_task_metrics': True,
}


E2E_METADATA = {
    'start_commands': [
        'apt-get update',
        'apt-get install rrdtool librrd-dev libpython-dev build-essential -y',
        'pip install rrdtool',
    ]
}
