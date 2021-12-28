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


class HcQueries:
    """
    HcQueries (high-cardinality queries) is a test utility to run queries against various loads
    (e.g. Large number of tables, schemas, query cardinality, etc). The test env (`hc`) used to run these queries
    can take sometime to setup.
    """

    def __init__(self, instance_docker, setup_timeout=60 * 6):
        self.EXPECTED_ROW_COUNT = 45_000
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

    def run_hc_queries(self, user, config=None):
        """
        Run a set of queries against the table `datadog_test.dbo.high_cardinality` in the background

        Args:
            user (str): The database user to run the queries.
            config (dict, optional): Configure how many threads will spin off for each kind
            of query and the post execution behavior.

        Config:
            `hc_threads`: The amount of threads to run high cardinality queries in the background.
            `slow_threads`: The amount of threads to run slow queries in the background.
        """
        if not config:
            config = {'hc_threads': 10, 'slow_threads': 10}

        self._is_running = True

        def run_hc_query_forever():
            conn = self._get_conn_for_user(user)
            while True:
                if not self._is_running:
                    break
                self._repeat_query(conn, self.create_high_cardinality_query(), 10)

        def run_slow_query_forever():
            conn = self._get_conn_for_user(user)
            while True:
                if not self._is_running:
                    break
                self._repeat_query(conn, self.create_slow_query(), 1)

        self._threads = [threading.Thread(target=run_hc_query_forever) for _ in range(config['hc_threads'])]
        self._threads.extend([threading.Thread(target=run_slow_query_forever) for _ in range(config['slow_threads'])])
        for t in self._threads:
            t.start()

    def stop_queries(self):
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

    def _get_conn_for_user(self, user):
        conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};'.format(
            self._instance_docker['driver'], self._instance_docker['host'], user, "Password12!"
        )
        # The initial startup is the slowest, this database is being loaded with high cardinality data.
        conn = pyodbc.connect(conn_str, timeout=60 * 8, autocommit=False)
        conn.timeout = DEFAULT_TIMEOUT
        return conn

    def _wait_for_table(self):
        timeout = time.time() + self._setup_timeout
        while True:
            with self._get_conn_for_user('bob').cursor() as cursor:
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

    @staticmethod
    def _repeat_query(conn, query, amount=5):
        for _ in range(amount):
            try:
                conn.execute(query)
            except Exception:
                # Ignore any exceptions because some queries may cause flakiness within tests. For example,
                # currently running slow queries may cause a timeout exception upon test cleanup.
                pass
