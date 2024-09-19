# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

import logging
import xml.etree.ElementTree as ET
import os
import pytest

from copy import copy, deepcopy
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.deadlocks import Deadlocks, MAX_PAYLOAD_BYTES
from mock import patch, MagicMock

from .common import CHECK_NAME
from .utils import create_deadlock

try:
    import pyodbc
except ImportError:
    pyodbc = None

@pytest.fixture
def dbm_instance(instance_docker):
    instance_docker['dbm'] = True
    # set a very small collection interval so the tests go fast
    instance_docker['query_activity'] = {
        'enabled': False,
    }
    # do not need query_metrics for these tests
    instance_docker['query_metrics'] = {'enabled': False}
    instance_docker['procedure_metrics'] = {'enabled': False}
    instance_docker['collect_settings'] = {'enabled': False}
    instance_docker['deadlocks_collection'] = {'enabled': True, 'collection_interval': 0.1}
    return copy(instance_docker)

def run_check_and_return_deadlock_payloads(dd_run_check, check, aggregator):
    dd_run_check(check)
    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    matched = []
    for event in dbm_activity:
        if "sqlserver_deadlocks" in event:
            matched.append(event)
    return matched


def _get_conn_for_user(instance_docker, user, timeout=1, _autocommit=False):
    # Make DB connection
    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};TrustServerCertificate=yes;'.format(
        instance_docker['driver'], instance_docker['host'], user, "Password12!"
    )
    conn = pyodbc.connect(conn_str, timeout=timeout, autocommit=_autocommit)
    conn.timeout = timeout
    return conn

@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_deadlocks(aggregator, dd_run_check, init_config, dbm_instance):
    sqlserver_check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    deadlock_payloads = run_check_and_return_deadlock_payloads(dd_run_check, sqlserver_check, aggregator)
    assert not deadlock_payloads, "shouldn't have sent an empty payload"

    created_deadlock = False
    # Rarely instead of creating a deadlock one of the transactions time outs
    for _ in range(0, 3):
        bob_conn = _get_conn_for_user(dbm_instance, 'bob', 3)
        fred_conn = _get_conn_for_user(dbm_instance, 'fred', 3)
        created_deadlock = create_deadlock(bob_conn, fred_conn)
        bob_conn.close()
        fred_conn.close()
        if created_deadlock:
            break
    try:
        assert created_deadlock, "Couldn't create a deadlock, exiting"
    except AssertionError as e:
        raise e

    dbm_instance_no_dbm = deepcopy(dbm_instance)
    dbm_instance_no_dbm['dbm'] = False
    sqlserver_check_no_dbm = SQLServer(CHECK_NAME, init_config, [dbm_instance_no_dbm])
    deadlock_payloads = run_check_and_return_deadlock_payloads(dd_run_check, sqlserver_check_no_dbm, aggregator)
    assert len(deadlock_payloads) == 0, "deadlock should be behind dbm"

    dbm_instance['dbm_enabled'] = True
    deadlock_payloads = run_check_and_return_deadlock_payloads(dd_run_check, sqlserver_check, aggregator)
    try:
        assert len(deadlock_payloads) == 1, "Should have collected one deadlock payload, but collected: {}.".format(
            len(deadlock_payloads)
        )
    except AssertionError as e:
        raise e
    deadlocks = deadlock_payloads[0]['sqlserver_deadlocks']
    found = 0
    for d in deadlocks:
        assert not "ERROR" in d, "Shouldn't have generated an error"
        assert isinstance(d, dict), "sqlserver_deadlocks should be a dictionary"
        try:
            root = ET.fromstring(d["xml"])
        except ET.ParseError as e:
            logging.error("deadlock events: %s", str(deadlocks))
            raise e
        process_list = root.find(".//process-list")
        for process in process_list.findall('process'):
            if process.find('inputbuf').text == "UPDATE [datadog_test-1].dbo.deadlocks SET b = b + 100 WHERE a = 2;":
                found += 1
    try:
        assert (
            found == 1
        ), "Should have collected the UPDATE statement in deadlock exactly once, but collected: {}.".format(found)
    except AssertionError as e:
        logging.error("deadlock XML: %s", str(d))
        raise e

DEADLOCKS_PLAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deadlocks")

def _load_test_deadlocks_xml(filename):
    with open(os.path.join(DEADLOCKS_PLAN_DIR, filename), 'r') as f:
        return f.read()

def test__create_deadlock_rows():
    deadlocks_obj = None
    with patch.object(Deadlocks, '__init__', return_value=None):
        deadlocks_obj = Deadlocks(None, None)
        deadlocks_obj._check = MagicMock()
        deadlocks_obj._log = MagicMock()
        deadlocks_obj._config = MagicMock()
        deadlocks_obj._config.obfuscator_options = {}
        deadlocks_obj._deadlock_payload_max_bytes = MAX_PAYLOAD_BYTES
    xml = _load_test_deadlocks_xml("sqlserver_deadlock_event.xml")
    with patch.object(Deadlocks, '_query_deadlocks', return_value=[["date placeholder", xml]]):
        rows = deadlocks_obj._create_deadlock_rows()
        assert len(rows) == 1, "Should have created one deadlock row"
        assert len(rows[0]["query_signatures"]) == 2, "Should have two query signatures"