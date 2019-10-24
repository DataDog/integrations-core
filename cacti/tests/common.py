# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
MYSQL_USERNAME = 'cactiuser'
MYSQL_PASSWORD = 'cactipass'
MYSQL_PORT = 13306
DATABASE = 'cacti'

# ID
CONTAINER_NAME = "dd-test-cacti"

RRD_PATH = '/var/www/html/cacti/rra'

INSTANCE_INTEGRATION = {
    'mysql_host': HOST,
    'mysql_user': MYSQL_USERNAME,
    'mysql_port': MYSQL_PORT,
    'mysql_password': MYSQL_PASSWORD,
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
