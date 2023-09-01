# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
MYSQL_USERNAME = 'cactiuser'
MYSQL_PASSWORD = 'cactipassword'
MYSQL_PORT = 13306
MYSQL_DATABASE = 'cacti_master'

RRD_PATH = '/var/www/html/cacti/rra'

INSTANCE_INTEGRATION = {
    'mysql_host': HOST,
    'mysql_user': MYSQL_USERNAME,
    'mysql_port': MYSQL_PORT,
    'mysql_password': MYSQL_PASSWORD,
    'mysql_db': MYSQL_DATABASE,
    'rrd_path': RRD_PATH,
    'collect_task_metrics': True,
}


E2E_METADATA = {
    'start_commands': [
        'apt-get update',
        'apt-get install rrdtool librrd-dev build-essential -y',
        'pip install rrdtool',
    ]
}
