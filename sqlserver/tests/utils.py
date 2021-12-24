# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import string
import time
from concurrent.futures.thread import ThreadPoolExecutor
from copy import copy
from random import choice, randrange, shuffle

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


class AppMarketQueries:
    '''
    AppMarketQueries is a test utility to run queries against the `app_market` test table.
    This table is high in cardinality and is useful to use for performance testing.
    A reference for the data can be found in `tests/compose-high-cardinality/dummy_data.sql`.
    The table takes approximately 2-4 min to setup and can only be used within the `hc` env.
    '''

    def __init__(self, instance_docker, setup_timeout=60 * 6) -> None:
        self.EXPECTED_ROW_COUNT = 1_000_000
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
        self._executor = ThreadPoolExecutor()

        # Ensure the test table is ready before proceeding.
        self._wait_for_table()

    def run_queries(self, user, config=None):
        '''
        Run a set of queries in the background.

        Args:
            user (str): The database user to run the queries.
            config (dict, optional): Configure how many threads each kind of query will
            spin off and the post execution behavior.

        Config:
            `hc_threads`: The amount of high cardinality queries to run in the background.
            `slow_threads`: The amount of slow queries to run in the background.
            `sleep`: How long to sleep after the query executions. This is useful if you
            want to put some strain on the database before proceeding with anything else.
        '''
        if not config:
            config = {'hc_threads': 10, 'slow_threads': 10, 'sleep': 60}

        self.is_running = True

        def run_hc_query_forever():
            while True:
                self.run_high_cardinality_query(user)
                if not self._is_running:
                    break

        def run_slow_query_forever():
            while True:
                self.run_slow_query(user)
                if not self._is_running:
                    break

        for _ in range(config['hc_threads']):
            self._executor.submit(run_hc_query_forever)

        for _ in range(config['slow_threads']):
            self._executor.submit(run_slow_query_forever)

        sleep = config['sleep']
        if sleep:
            time.sleep(sleep)

    def stop_queries(self):
        '''Stop background query executions and cleanup the thread executor.'''
        self._is_running = False
        self._executor.shutdown(wait=True)

    def run_high_cardinality_query(self, user):
        conn = self._get_conn_for_user(user)
        conn.execute(self.create_high_cardinality_query())

    def run_slow_query(self, user):
        conn = self._get_conn_for_user(user)
        conn.execute(self.create_slow_query())

    def create_high_cardinality_query(self):
        '''Creates a high cardinality query by shuffling the columns.'''
        columns = copy(self.columns)
        shuffle(columns)
        return 'SELECT {col} FROM app_market WHERE id = {id}'.format(
            col=','.join(columns), id=randrange(1, self.EXPECTED_ROW_COUNT)
        )

    def create_slow_query(self):
        '''Creates a slow running query by trying to match a pattern that may or may not exist.'''
        columns = copy(self.columns)
        shuffle(columns)
        return 'SELECT TOP 10 {col} FROM app_market WHERE app_btc_addr LIKE \'%{pattern}%\''.format(
            col={columns[0]}, pattern=self._create_rand_string()
        )

    def _get_conn_for_user(self, user):
        conn_str = 'DRIVER={};Server={};Database=datadog_test;UID={};PWD={};'.format(
            self._instance_docker['driver'], self._instance_docker['host'], user, "Password12!"
        )
        conn = pyodbc.connect(conn_str, timeout=DEFAULT_TIMEOUT, autocommit=False)
        conn.timeout = DEFAULT_TIMEOUT
        return conn

    def _wait_for_table(self):
        timeout = time.time() + self._setup_timeout
        while True:
            with self._get_conn_for_user('bob').cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM app_market')
                count = cursor.fetchone()[0]
                if count >= self.EXPECTED_ROW_COUNT:
                    break
                elif time.time() > timeout:
                    raise Exception("Waiting for the test tables timed out.")
                time.sleep(5)

    @staticmethod
    def _create_rand_string(length=5):
        return ''.join(choice(string.ascii_lowercase + string.digits) for _ in range(length))
