# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import string
import threading
from copy import copy
from random import choice, randint, shuffle

import pyodbc
import pytest

from datadog_checks.dev.utils import running_on_windows_ci


def is_always_on():
    return os.environ["COMPOSE_FOLDER"] == 'compose-ha'


windows_ci = pytest.mark.skipif(not running_on_windows_ci(), reason='Test can only be run on Windows CI')
not_windows_ci = pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')

always_on = pytest.mark.skipif(not is_always_on(), reason='Test can only be run on AlwaysOn SQLServer instances')
# Do not run in environments that specify Windows ADO drivers. This is mainly important for e2e tests where the agent
# is running in Docker where we don't bundle any ADO drivers in the container.
not_windows_ado = pytest.mark.skipif(
    os.environ.get("WINDOWS_SQLSERVER_DRIVER", "odbc") != 'odbc', reason='Test cannot be run using Windows ADO drivers.'
)
high_cardinality_only = pytest.mark.skipif(
    'compose-high-cardinality' not in os.environ["COMPOSE_FOLDER"],
    reason='Test can only be run in the high cardinality env.',
)


class HighCardinalityQueries:
    """
    HighCardinalityQueries is a test utility to run queries against a high cardinality database (e.g. Large number of
    tables, schemas, query cardinality, etc). You must use the `high-cardinality` env to utilize this.
    """

    DEFAULT_TIMEOUT = 30
    EXPECTED_OBJ_COUNT = 2000
    EXPECTED_ROW_COUNT = 100

    def __init__(self, db_instance_config):
        self.columns = [
            'col1_txt',
            'col2_txt',
            'col3_txt',
            'col4_txt',
            'col5_txt',
            'col6_txt',
            'col7_txt',
            'col8_txt',
            'col9_txt',
            'col10_txt',
            'col11_float',
            'col12_float',
            'col13_float',
            'col14_int',
            'col15_int',
            'col16_int',
            'col17_date',
        ]
        self._db_instance_config = db_instance_config
        self._is_running = False
        self._threads = []

    def is_ready(self):
        """
        Checks if the database is in a 'ready' state. A 'ready' state is defined as having the expected
        object (user, schema, and tables) and row count.
        """
        cursor = self.get_conn().cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM datadog_test.sys.database_principals WHERE name LIKE \'high_cardinality_user_%\''
        )
        user_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM datadog_test.sys.schemas WHERE name LIKE \'high_cardinality_schema%\'')
        schema_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM datadog_test.sys.tables')
        table_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM datadog_test.dbo.high_cardinality')
        row_count = cursor.fetchone()[0]
        return (
            user_count >= HighCardinalityQueries.EXPECTED_OBJ_COUNT
            and schema_count >= HighCardinalityQueries.EXPECTED_OBJ_COUNT
            and table_count >= HighCardinalityQueries.EXPECTED_OBJ_COUNT
            and row_count >= HighCardinalityQueries.EXPECTED_ROW_COUNT
        )

    def start_background(self, config=None):
        """
        Run a set of queries against the table `datadog_test.dbo.high_cardinality` in the background

        Args:
            config (dict, optional): Configure how many threads will spin off for each kind of query.

        Config:
            NOTE: Each 'thread' creates a new connection.

            - `hc_threads`: The amount of threads to run high cardinality queries in the background.

            - `slow_threads`: The amount of threads to run slow queries in the background.

            - `complex_threads`: The amount of threads to run complex queries in the background.
        """
        if not config:
            config = {'hc_threads': 10, 'slow_threads': 10, 'complex_threads': 10}

        self._is_running = True

        def _run_hc_query_forever():
            conn = self.get_conn()
            while True:
                if not self._is_running:
                    break
                self.run_query_and_ignore_exception(conn, self.create_high_cardinality_query())

        def _run_slow_query_forever():
            conn = self.get_conn()
            while True:
                if not self._is_running:
                    break
                self.run_query_and_ignore_exception(conn, self.create_slow_query())

        def _run_complex_query_forever():
            conn = self.get_conn()
            while True:
                if not self._is_running:
                    break
                self.run_query_and_ignore_exception(conn, self.create_complex_query())

        self._threads = [threading.Thread(target=_run_hc_query_forever) for _ in range(config['hc_threads'])]
        self._threads.extend([threading.Thread(target=_run_slow_query_forever) for _ in range(config['slow_threads'])])
        self._threads.extend(
            [threading.Thread(target=_run_complex_query_forever) for _ in range(config['complex_threads'])]
        )
        for t in self._threads:
            t.start()

    def stop(self):
        """Stop background query executions."""
        self._is_running = False
        for t in self._threads:
            t.join()

    def create_high_cardinality_query(self):
        """Creates a high cardinality query by shuffling the columns."""
        columns = copy(self.columns)
        shuffle(columns)
        return 'SELECT {col} FROM datadog_test.dbo.high_cardinality WHERE id = {id}'.format(
            col=','.join(columns), id=randint(1, HighCardinalityQueries.EXPECTED_ROW_COUNT)
        )

    def create_slow_query(self):
        """Creates a slow running query by trying to match a pattern that may or may not exist."""
        columns = copy(self.columns)
        shuffle(columns)
        return 'SELECT TOP 10 {col} FROM datadog_test.dbo.high_cardinality WHERE col2_txt LIKE \'%{pattern}%\''.format(
            col={columns[0]}, pattern=self._create_rand_string()
        )

    def create_complex_query(self):
        """Creates a complex query to produce complicated execution plans."""
        columns = copy(self.columns)
        shuffle(columns)
        query = """\
        SELECT
            {col}
        FROM
            datadog_test.dbo.high_cardinality AS hc1
            JOIN (
                SELECT
                    id,
                    COUNT(*) col12_float
                FROM
                    datadog_test.dbo.high_cardinality AS hc2
                WHERE
                    hc2.col1_txt LIKE '%-%'
                    AND hc2.col14_int > (
                        SELECT
                            AVG(hc3.col15_int)
                        FROM
                            datadog_test.dbo.high_cardinality AS hc3)
                    GROUP BY
                        hc2.id) AS hc4 ON hc4.id = hc1.id
            JOIN datadog_test.dbo.high_cardinality AS hc5 ON hc5.id = hc1.id
        WHERE
            CAST(hc5.col17_date AS VARCHAR)
            IN('2003-04-23', '2043-09-10', '1996-08-08')
            AND hc5.col13_float IS NOT NULL
            AND hc5.col17_date NOT LIKE '21%';
        """
        # Select a range of random columns and prefix to match our alias
        return query.format(col=','.join(['hc1.' + col for col in columns[: randint(1, len(columns) - 1)]]))

    def get_conn(self):
        conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};TrustServerCertificate=yes;'.format(
            self._db_instance_config['driver'],
            self._db_instance_config['host'],
            self._db_instance_config['username'],
            self._db_instance_config['password'],
        )
        return pyodbc.connect(conn_str, timeout=HighCardinalityQueries.DEFAULT_TIMEOUT, autocommit=False)

    @staticmethod
    def run_query_and_ignore_exception(conn, query):
        """
        This is useful if you want to ignore query execution exceptions. For instance, if you execute a slow query
        in the background and a test orders a cleanup, the slow executing query may throw an unwanted exception.
        """
        try:
            conn.execute(query)
        except Exception:
            pass

    @staticmethod
    def _create_rand_string(length=5):
        return ''.join(choice(string.ascii_lowercase + string.digits) for _ in range(length))
