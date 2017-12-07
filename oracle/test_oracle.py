# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import logging
import time

# 3p
from nose.plugins.attrib import attr
import cx_Oracle

# project
from tests.checks.common import AgentCheckTest

logging.basicConfig()

"""
Using the "system" user as permission granting not available
for default "system" user

Set up Oracle instant client:
http://jasonstitt.com/cx_oracle_on_os_x

Set:
export ORACLE_HOME=/opt/oracle/instantclient_12_1/
export DYLD_LIBRARY_PATH="$ORACLE_HOME:$DYLD_LIBRARY_PATH"
"""

CONFIG = {
    'init_config': {},
    'instances': [{
        'server': 'localhost:1521',
        'user': 'system',
        'password': 'oracle',
        'service_name': 'xe',
    }]
}

SERVICE_CHECK_NAME = 'oracle.can_connect'
METRICS = [
    'oracle.tablespace.used',
    'oracle.tablespace.size',
    'oracle.tablespace.in_use',
    'oracle.buffer_cachehit_ratio',
    'oracle.cursor_cachehit_ratio',
    'oracle.library_cachehit_ratio',
    'oracle.shared_pool_free',
    'oracle.physical_reads',
    'oracle.physical_writes',
    'oracle.enqueue_timeouts',
    'oracle.gc_cr_receive_time',
    'oracle.cache_blocks_corrupt',
    'oracle.cache_blocks_lost',
    'oracle.logons',
    'oracle.active_sessions',
    'oracle.long_table_scans',
    'oracle.service_response_time',
    'oracle.user_rollbacks',
    'oracle.sorts_per_user_call',
    'oracle.rows_per_sort',
    'oracle.disk_sorts',
    'oracle.memory_sorts_ratio',
    'oracle.database_wait_time_ratio',
    'oracle.enqueue_timeouts',
    'oracle.session_limit_usage',
    'oracle.session_count',
    'oracle.temp_space_used',
]

@attr(requires='oracle')
class TestOracle(AgentCheckTest):
    """Basic Test for oracle integration."""
    CHECK_NAME = 'oracle'

    def setUp(self):
        conn_string = 'cx_Oracle/welcome@//localhost:1521/xe'
        connection = cx_Oracle.connect(conn_string)

        # mess around a bit to pupulate metrics
        cursor = connection.cursor()
        cursor.execute("select 'X' from dual")

        # truncate
        cursor.execute("truncate table TestTempTable")

        # insert
        rows = [{u"value": n} for n in range(250)]
        cursor.arraysize = 100
        statement = "insert into TestTempTable (IntCol) values (:value)"
        cursor.executemany(statement, rows)
        connection.commit()

        # select
        cursor.execute("select count(*) from TestTempTable")
        _, = cursor.fetchone()

        # wait to populate
        time.sleep(90)

    def testOracle(self):
        self.run_check_twice(CONFIG)

        for m in METRICS:
            self.assertMetric(m, at_least=1)

        self.assertServiceCheck(SERVICE_CHECK_NAME)
        self.coverage_report()
