# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

from datadog_checks.utils.common import get_docker_hostname
import psycopg2


HOST = get_docker_hostname()
PORT = '6432'
USER = 'postgres'
PASS = 'datadog'
DB = 'datadog_test'


def get_version():
    """
    Retrieve PgBouncer version
    """
    regex = r'\d\.\d\.\d'
    conn = psycopg2.connect(host=HOST, port=PORT, user=USER, password=PASS,
                            database='pgbouncer', connect_timeout=1)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute('SHOW VERSION;')
    if conn.notices:
        res = re.findall(regex, conn.notices[0])
        if res:
            return tuple(int(s) for s in res[0].split('.'))
    return None
