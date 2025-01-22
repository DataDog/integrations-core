# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

import concurrent
import logging
import os
import re
import xml.etree.ElementTree as ET
from copy import copy, deepcopy
from threading import Event

import pytest
from mock import patch

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.database_metrics.xe_session_metrics import XE_EVENT_FILE, XE_RING_BUFFER
from datadog_checks.sqlserver.deadlocks import (
    PAYLOAD_QUERY_SIGNATURE,
    PAYLOAD_TIMESTAMP,
    Deadlocks,
)
from datadog_checks.sqlserver.queries import (
    DEADLOCK_TIMESTAMP_ALIAS,
    DEADLOCK_XML_ALIAS,
    XE_SESSION_DATADOG,
    XE_SESSION_SYSTEM,
)

from .common import CHECK_NAME

try:
    import pyodbc
except ImportError:
    pyodbc = None


@pytest.fixture(scope="session")
def dbm_instance(instance_session_default):
    instance_docker = deepcopy(instance_session_default)
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
    return instance_docker


def _run_check_and_get_deadlock_payloads(dd_run_check, check, aggregator):
    dbm_activity = _run_check_and_get_activity_samples(dd_run_check, check, aggregator)
    return _get_deadlocks_payload(dbm_activity)


def _run_check_and_get_activity_samples(dd_run_check, check, aggregator):
    dd_run_check(check)
    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    return dbm_activity


def _get_deadlocks_payload(dbm_activity):
    matched = []
    for event in dbm_activity:
        if "sqlserver_deadlocks" in event:
            matched.append(event)
    return matched


def _get_conn_for_user(instance_docker, user, password="Password12!"):
    conn_str = (
        f"DRIVER={instance_docker['driver']};"
        f"Server={instance_docker['host']};"
        "Database=master;"
        f"UID={user};"
        f"PWD={password};"
        "TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str, autocommit=False)
    return conn


def _run_first_deadlock_query(conn, event1, event2):
    exception_text = ""
    try:
        conn.cursor().execute("BEGIN TRAN foo;")
        conn.cursor().execute("UPDATE [datadog_test-1].dbo.deadlocks SET b = b + 10 WHERE a = 1;")
        event1.set()
        event2.wait()
        conn.cursor().execute("UPDATE [datadog_test-1].dbo.deadlocks SET b = b + 100 WHERE a = 2;")
    except Exception as e:
        # Exception is expected due to a deadlock
        exception_text = str(e)
        pass
    conn.commit()
    return exception_text


def _run_second_deadlock_query(conn, event1, event2):
    exception_text = ""
    try:
        event1.wait()
        conn.cursor().execute("BEGIN TRAN bar;")
        conn.cursor().execute("UPDATE [datadog_test-1].dbo.deadlocks SET b = b + 10 WHERE a = 2;")
        event2.set()
        conn.cursor().execute("UPDATE [datadog_test-1].dbo.deadlocks SET b = b + 20 WHERE a = 1;")
    except Exception as e:
        # Exception is expected due to a deadlock
        exception_text = str(e)
        pass
    conn.commit()
    return exception_text


@pytest.fixture(scope="session")
def _create_deadlock(dd_environment, dbm_instance):
    bob_conn = _get_conn_for_user(dbm_instance, 'bob')
    fred_conn = _get_conn_for_user(dbm_instance, 'fred')
    executor = concurrent.futures.thread.ThreadPoolExecutor(2)
    event1 = Event()
    event2 = Event()
    futures_first_query = executor.submit(_run_first_deadlock_query, bob_conn, event1, event2)
    futures_second_query = executor.submit(_run_second_deadlock_query, fred_conn, event1, event2)
    exception_1_text = futures_first_query.result()
    exception_2_text = futures_second_query.result()
    executor.shutdown()
    bob_conn.close()
    fred_conn.close()
    if "deadlock" in exception_1_text or "deadlock" in exception_2_text:
        return
    raise Exception(
        f"Couldn't create a deadlock | batch output 1: {exception_1_text} | batch output 2: {exception_2_text}"
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.usefixtures('_create_deadlock')
@pytest.mark.parametrize("convert_xml_to_str", [False, True])
@pytest.mark.parametrize(
    "xe_session_name, xe_session_target",
    [
        [XE_SESSION_DATADOG, XE_RING_BUFFER],
        [XE_SESSION_SYSTEM, XE_EVENT_FILE],
    ],
)
def test_deadlocks(aggregator, dd_run_check, dbm_instance, convert_xml_to_str, xe_session_name, xe_session_target):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    check.deadlocks._force_convert_xml_to_str = convert_xml_to_str
    check.deadlocks._xe_session_name = xe_session_name
    check.deadlocks._xe_session_target = xe_session_target

    dbm_instance['dbm_enabled'] = True
    deadlock_payloads = _run_check_and_get_deadlock_payloads(dd_run_check, check, aggregator)
    try:
        assert (
            len(deadlock_payloads) == 1
        ), f"Should have collected one deadlock payload, but collected: {len(deadlock_payloads)}"
    except AssertionError as e:
        raise e
    deadlocks = deadlock_payloads[0]['sqlserver_deadlocks']
    found = 0
    for d in deadlocks:
        assert "ERROR" not in d, "Shouldn't have generated an error"
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
        logging.error("deadlock payload: %s", str(deadlocks))
        raise e


@pytest.mark.usefixtures('dd_environment')
def test_no_empty_deadlocks_payloads(dd_run_check, init_config, dbm_instance, aggregator):
    check = SQLServer(CHECK_NAME, init_config, [dbm_instance])
    with patch.object(
        Deadlocks,
        '_query_deadlocks',
        return_value=[],
    ):
        assert not _run_check_and_get_deadlock_payloads(
            dd_run_check, check, aggregator
        ), "shouldn't have sent an empty payload"


@pytest.mark.usefixtures('dd_environment')
def test_deadlocks_behind_dbm(dd_run_check, init_config, dbm_instance):
    dbm_instance_no_dbm = deepcopy(dbm_instance)
    dbm_instance_no_dbm['dbm'] = False
    check = SQLServer(CHECK_NAME, init_config, [dbm_instance_no_dbm])
    xml = _load_test_deadlocks_xml("sqlserver_deadlock_event.xml")
    with patch.object(
        Deadlocks,
        '_query_deadlocks',
        return_value=[{DEADLOCK_TIMESTAMP_ALIAS: "2024-09-20T12:07:16.647000", DEADLOCK_XML_ALIAS: xml}],
    ) as mocked_function:
        dd_run_check(check)
        mocked_function.assert_not_called()


@pytest.mark.usefixtures('dd_environment')
def test_xe_session(dd_run_check, dbm_instance):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    assert check.deadlocks._xe_session_name == XE_SESSION_DATADOG


DEADLOCKS_PLAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deadlocks")


def _load_test_deadlocks_xml(filename):
    with open(os.path.join(DEADLOCKS_PLAN_DIR, filename), 'r') as f:
        return f.read()


@pytest.fixture
def deadlocks_collection_instance(instance_docker):
    instance_docker['dbm'] = True
    instance_docker['deadlocks_collection'] = {
        'enabled': True,
        'collection_interval': 1.0,
    }
    instance_docker['min_collection_interval'] = 1
    # do not need other dbm metrics
    instance_docker['query_activity'] = {'enabled': False}
    instance_docker['query_metrics'] = {'enabled': False}
    instance_docker['procedure_metrics'] = {'enabled': False}
    instance_docker['collect_settings'] = {'enabled': False}
    return copy(instance_docker)


def _get_deadlock_obj(deadlocks_collection_instance):
    check = SQLServer(CHECK_NAME, {}, [deadlocks_collection_instance])
    return check.deadlocks


def test__create_deadlock_rows(deadlocks_collection_instance):
    deadlocks_obj = _get_deadlock_obj(deadlocks_collection_instance)
    xml = _load_test_deadlocks_xml("sqlserver_deadlock_event.xml")
    with patch.object(
        Deadlocks,
        '_query_deadlocks',
        return_value=[{DEADLOCK_TIMESTAMP_ALIAS: "2024-09-20T12:07:16.647000", DEADLOCK_XML_ALIAS: xml}],
    ):
        rows = deadlocks_obj._create_deadlock_rows()
        assert len(rows) == 1, "Should have created one deadlock row"
        row = rows[0]
        assert row[PAYLOAD_TIMESTAMP], "Should have a timestamp"
        query_signatures = row[PAYLOAD_QUERY_SIGNATURE]
        assert len(query_signatures) == 2, "Should have two query signatures"
        first_mapping = query_signatures[0]
        assert "spid" in first_mapping, "Should have spid in query signatures"
        assert isinstance(first_mapping["spid"], int), "spid should be an int"


def test_deadlock_xml_bad_format(deadlocks_collection_instance):
    test_xml = """
    <event name="xml_deadlock_report" package="sqlserver" timestamp="2024-08-20T08:30:35.762Z">
     <data name="xml_report">
      <type name="xml" package="package0"/>
      <value>
       <deadlock>
        <victim-list>
         <victimProcess id="process12108eb088"/>
        </victim-list>
       </deadlock>
      </value>
     </data>
    </event>
    """
    deadlocks_obj = _get_deadlock_obj(deadlocks_collection_instance)
    root = ET.fromstring(test_xml)
    try:
        deadlocks_obj._obfuscate_xml(root)
    except Exception as e:
        result = str(e)
        assert result == "process-list element not found. The deadlock XML is in an unexpected format."
    else:
        AssertionError("Should have raised an exception for bad XML format")


def test_deadlock_calls_obfuscator(deadlocks_collection_instance):
    test_xml = """
    <event name="xml_deadlock_report" package="sqlserver" timestamp="2024-08-20T08:30:35.762Z">
     <data name="xml_report">
      <type name="xml" package="package0"/>
      <value>
       <deadlock>
        <victim-list>
         <victimProcess id="process12108eb088"/>
        </victim-list>
        <process-list>
         <process id="process12108eb088">
          <executionStack>
           <frame procname="adhoc" line="1" stmtstart="38" stmtend="180" sqlhandle="0">\nunknown    </frame>
           <frame procname="adhoc" line="1" stmtend="128" sqlhandle="0">\nunknown    </frame>
          </executionStack>
          <inputbuf>\nUPDATE [datadog_test-1].dbo.deadlocks SET b = b + 100 WHERE a = 2;   </inputbuf>
         </process>
         <process id="process1215b77088">
          <executionStack>
           <frame procname="adhoc" line="1" stmtstart="38" stmtend="180" sqlhandle="0">\nunknown    </frame>
           <frame procname="adhoc" line="1" stmtend="126" sqlhandle="0">\nunknown    </frame>
          </executionStack>
          <inputbuf>\nUPDATE [datadog_test-1].dbo.deadlocks SET b = b + 20 WHERE a = 1;   </inputbuf>
         </process>
        </process-list>
       </deadlock>
      </value>
     </data>
    </event>
    """

    expected_xml_string = (
        "<event name=\"xml_deadlock_report\" package=\"sqlserver\" timestamp=\"2024-08-20T08:30:35.762Z\"> "
        "<data name=\"xml_report\"> "
        "<type name=\"xml\" package=\"package0\" /> "
        "<value> "
        "<deadlock> "
        "<victim-list> "
        "<victimProcess id=\"process12108eb088\" /> "
        "</victim-list> "
        "<process-list> "
        "<process id=\"process12108eb088\"> "
        "<executionStack> "
        "<frame procname=\"adhoc\" line=\"1\" stmtstart=\"38\" stmtend=\"180\" sqlhandle=\"0\">obfuscated</frame> "
        "<frame procname=\"adhoc\" line=\"1\" stmtend=\"128\" sqlhandle=\"0\">obfuscated</frame> "
        "</executionStack> "
        "<inputbuf>obfuscated</inputbuf> "
        "</process> "
        "<process id=\"process1215b77088\"> "
        "<executionStack> "
        "<frame procname=\"adhoc\" line=\"1\" stmtstart=\"38\" stmtend=\"180\" sqlhandle=\"0\">obfuscated</frame> "
        "<frame procname=\"adhoc\" line=\"1\" stmtend=\"126\" sqlhandle=\"0\">obfuscated</frame> "
        "</executionStack> "
        "<inputbuf>obfuscated</inputbuf> "
        "</process> "
        "</process-list> "
        "</deadlock> "
        "</value> "
        "</data> "
        "</event>"
    )

    with patch('datadog_checks.sqlserver.deadlocks.Deadlocks.obfuscate_no_except_wrapper', return_value="obfuscated"):
        deadlocks_obj = _get_deadlock_obj(deadlocks_collection_instance)
        root = ET.fromstring(test_xml)
        deadlocks_obj._obfuscate_xml(root)
        result_string = ET.tostring(root, encoding='unicode')
        result_string = result_string.replace('\t', '').replace('\n', '')
        result_string = re.sub(r'\s{2,}', ' ', result_string)
        assert expected_xml_string == result_string
