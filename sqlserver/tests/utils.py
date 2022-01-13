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

windows_ci = pytest.mark.skipif(not running_on_windows_ci(), reason='Test can only be run on Windows CI')
not_windows_ci = pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
always_on = pytest.mark.skipif(
    os.environ["COMPOSE_FOLDER"] != 'compose-ha', reason='Test can only be run on AlwaysOn SQLServer instances'
)
high_cardinality_only = pytest.mark.skipif(
    os.environ["COMPOSE_FOLDER"] != 'compose-high-cardinality',
    reason='Test can only be run in the high cardinality env.',
)


class HighCardinalityQueries:
    """
    HighCardinalityQueries is a test utility to run queries against a high cardinality database
    (e.g. Large number of tables, schemas, query cardinality, etc). You must use the `hc` env to utilize this.
    """

    DEFAULT_TIMEOUT = 30

    def __init__(self, instance_docker=None):
        self.EXPECTED_USER_COUNT = 10000
        self.EXPECTED_SCHEMA_COUNT = 10000
        self.EXPECTED_TABLE_COUNT = 10000
        self.EXPECTED_ROW_COUNT = 100000
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
        self._instance_docker = instance_docker
        self._is_running = False
        self._threads = []

    def start_background(self, user, config=None):
        """
        Run a set of queries against the table `datadog_test.dbo.high_cardinality` in the background

        Args:
            user (str): The database user to run the queries.
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

        def run_hc_query_forever():
            conn = self.get_conn_for_user(user)
            while True:
                if not self._is_running:
                    break
                self.run_query_and_ignore_exception(conn, self.create_high_cardinality_query())

        def run_slow_query_forever():
            conn = self.get_conn_for_user(user)
            while True:
                if not self._is_running:
                    break
                self.run_query_and_ignore_exception(conn, self.create_slow_query())

        def run_complex_query_forever():
            conn = self.get_conn_for_user(user)
            while True:
                if not self._is_running:
                    break
                self.run_query_and_ignore_exception(conn, self.create_complex_query())

        self._threads = [threading.Thread(target=run_hc_query_forever) for _ in range(config['hc_threads'])]
        self._threads.extend([threading.Thread(target=run_slow_query_forever) for _ in range(config['slow_threads'])])
        self._threads.extend(
            [threading.Thread(target=run_complex_query_forever) for _ in range(config['complex_threads'])]
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
            col=','.join(columns), id=randint(1, self.EXPECTED_ROW_COUNT)
        )

    def create_slow_query(self):
        """Creates a slow running query by trying to match a pattern that may or may not exist."""
        columns = copy(self.columns)
        shuffle(columns)
        return (
            'SELECT TOP 10 {col} FROM datadog_test.dbo.high_cardinality WHERE col2_txt LIKE \'%{pattern}%\''.format(
                col={columns[0]}, pattern=self._create_rand_string()
            )
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

    def get_conn_for_user(self, user):
        conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};'.format(
            self._instance_docker['driver'], self._instance_docker['host'], user, "Password12!"
        )
        conn = pyodbc.connect(conn_str, timeout=HighCardinalityQueries.DEFAULT_TIMEOUT, autocommit=False)
        conn.timeout = HighCardinalityQueries.DEFAULT_TIMEOUT
        return conn

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
