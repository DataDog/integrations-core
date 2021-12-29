# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import string
import threading
import time
from copy import copy
from random import choice, randint, shuffle

import pyodbc
import pytest

from datadog_checks.dev.utils import running_on_windows_ci

from .conftest import DEFAULT_TIMEOUT

windows_ci = pytest.mark.skipif(not running_on_windows_ci(), reason='Test can only be run on Windows CI')
not_windows_ci = pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
always_on = pytest.mark.skipif(
    os.environ["COMPOSE_FOLDER"] == 'compose', reason='Test can only be run on AlwaysOn SQLServer instances'
)
hc_only = pytest.mark.skipif(
    os.environ["COMPOSE_FOLDER"] != 'compose-high-cardinality',
    reason='Test can only be run in the high cardinality (hc) env.',
)


class HighCardinalityQueries:
    """
    HighCardinalityQueries is a test utility to run queries against a high-cardinality database
    (e.g. Large number of tables, schemas, query cardinality, etc). You must use the `hc` env to utilize this and the
    setup time can be long.
    """

    TIMEOUT = 60 * 8

    def __init__(self, instance_docker, setup_timeout=TIMEOUT):
        self.EXPECTED_ROW_COUNT = 500_000
        self.columns = [
            'id',
            'guid',
            'app_name',
            'app_version',
            'app_image',
            'app_image_base64',
            'app_ip_v6',
            'app_btc_addr',
            'app_slogan',
            'app_priority',
            'app_permissions',
            'subscription_renewal',
            'primary_contact',
            'user_firstname',
            'user_lastname',
            'user_city',
            'user_state',
            'user_country',
            'loc_lat',
            'loc_long',
            'user_ssn',
            'user_card',
            'user_card_type',
            'created_at',
            'updated_at',
        ]

        self._instance_docker = instance_docker
        self._setup_timeout = setup_timeout
        self._is_running = False
        self._threads = []

        # Ensure the test table is ready before proceeding.
        self._wait_for_table()

    def run(self, user, config=None):
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
                conn.execute(self.create_high_cardinality_query())

        def run_slow_query_forever():
            conn = self.get_conn_for_user(user)
            while True:
                if not self._is_running:
                    break
                conn.execute(self.create_slow_query())

        def run_complex_query_forever():
            conn = self.get_conn_for_user(user)
            while True:
                if not self._is_running:
                    break
                conn.execute(self.create_complex_query())

        self._threads = [threading.Thread(target=run_hc_query_forever) for _ in range(config['hc_threads'])]
        self._threads.extend([threading.Thread(target=run_slow_query_forever) for _ in range(config['slow_threads'])])
        self._threads.extend(
            [threading.Thread(target=run_complex_query_forever) for _ in range(config['complex_threads'])]
        )
        for t in self._threads:
            t.start()

    def stop(self):
        """Stop background query executions and cleanup the thread executor."""
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
            'SELECT TOP 10 {col} FROM datadog_test.dbo.high_cardinality WHERE app_btc_addr LIKE \'%{pattern}%\''.format(
                col={columns[0]}, pattern=self._create_rand_string()
            )
        )

    def create_complex_query(self):
        """Creates a complex query to produce complicated execution plans."""
        columns = copy(self.columns)
        shuffle(columns)
        query = """
        SELECT
            {col}
        FROM
            datadog_test.dbo.high_cardinality AS hc1
            JOIN (
                SELECT
                    id,
                    COUNT(*) app_priority
                FROM
                    datadog_test.dbo.high_cardinality AS hc2
                WHERE
                    hc2.app_version LIKE '8.%'
                    AND hc2.loc_lat > (
                        SELECT
                            AVG(hc3.loc_lat)
                        FROM
                            datadog_test.dbo.high_cardinality AS hc3)
                    GROUP BY
                        hc2.id) AS hc4 ON hc4.id = hc1.id
            JOIN datadog_test.dbo.high_cardinality AS hc5 ON hc5.id = hc1.id
        WHERE
            CAST(hc5.subscription_renewal AS VARCHAR)
            IN('Once', 'Yearly', 'Weekly')
            AND hc5.user_state IS NOT NULL
            AND hc5.app_version NOT LIKE '0.%';
        """
        # Select a range of random columns and prefix to match our alias
        return query.format(col=','.join(['hc1.' + col for col in columns[: randint(1, len(columns) - 1)]]))

    def get_conn_for_user(self, user):
        conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};'.format(
            self._instance_docker['driver'], self._instance_docker['host'], user, "Password12!"
        )
        conn = pyodbc.connect(conn_str, timeout=HighCardinalityQueries.TIMEOUT, autocommit=False)
        conn.timeout = DEFAULT_TIMEOUT
        return conn

    def _wait_for_table(self):
        timeout = time.time() + self._setup_timeout
        while True:
            with self.get_conn_for_user('bob').cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM datadog_test.dbo.high_cardinality')
                count = cursor.fetchone()[0]
                if count >= self.EXPECTED_ROW_COUNT:
                    break
                elif time.time() > timeout:
                    raise Exception("Waiting for the test tables timed out.")
                time.sleep(5)

    @staticmethod
    def _create_rand_string(length=5):
        return ''.join(choice(string.ascii_lowercase + string.digits) for _ in range(length))
