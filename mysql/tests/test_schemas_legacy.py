# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Unit tests for legacy schema collector (MySqlSchemaCollectorLegacy).
Used for MySQL < 8.0.19 and MariaDB < 10.5.0.
"""

import json
import time
from unittest import mock

import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.schemas_legacy import MySqlSchemaCollectorLegacy, SubmitData

from . import common
from .utils import deep_compare


class DummyLogger:
    def debug(*args):
        pass

    def error(*args):
        pass


def set_up_submitter_unit_test():
    submitted_data = []
    base_event = {
        "host": "some",
        "agent_version": 0,
        "dbms": "sqlserver",
        "kind": "sqlserver_databases",
        "collection_interval": 1200,
        "dbms_version": "some",
        "tags": "some",
        "cloud_metadata": "some",
    }

    def submitData(data):
        submitted_data.append(data)

    dataSubmitter = SubmitData(submitData, base_event, DummyLogger())
    return dataSubmitter, submitted_data


@pytest.mark.unit
def test_submit_data():
    """Test that SubmitData correctly batches and submits schema metadata"""
    dataSubmitter, submitted_data = set_up_submitter_unit_test()

    dataSubmitter.store_db_infos(
        [
            {"name": "test_db1", "default_character_set_name": "latin1"},
            {"name": "test_db2", "default_character_set_name": "latin1"},
        ]
    )

    dataSubmitter.store("test_db1", [1, 2], 5)
    dataSubmitter.store("test_db2", [1, 2], 5)
    assert dataSubmitter.columns_since_last_submit() == 10
    dataSubmitter.store("test_db1", [1, 2], 10)

    dataSubmitter.submit()

    assert dataSubmitter.columns_since_last_submit() == 0

    expected_data = {
        "host": "some",
        "agent_version": 0,
        "dbms": "sqlserver",
        "kind": "sqlserver_databases",
        "collection_interval": 1200,
        "dbms_version": "some",
        "tags": "some",
        "cloud_metadata": "some",
        "metadata": [
            {"name": "test_db1", "default_character_set_name": "latin1", "tables": [1, 2, 1, 2]},
            {"name": "test_db2", "default_character_set_name": "latin1", "tables": [1, 2]},
        ],
    }

    data = json.loads(submitted_data[0])
    data.pop("timestamp")
    assert deep_compare(data, expected_data)


@pytest.mark.unit
def test_fetch_throws():
    """Test that schema collector handles fetch errors gracefully"""
    check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    databases_data = MySqlSchemaCollectorLegacy({}, check, check._config)
    with (
        mock.patch('time.time', side_effect=[0, 9999999]),
        mock.patch(
            'datadog_checks.mysql.schemas_legacy.MySqlSchemaCollectorLegacy._get_tables',
            return_value=[{"name": "mytable1"}, {"name": "mytable2"}],
        ),
        mock.patch('datadog_checks.mysql.schemas_legacy.MySqlSchemaCollectorLegacy._get_tables', return_value=[1, 2]),
    ):
        with pytest.raises(StopIteration):
            databases_data._fetch_database_data("dummy_cursor", time.time(), "my_db")


@pytest.mark.unit
def test_submit_is_called_if_too_many_columns():
    """Test that data is submitted when column count exceeds limit"""
    check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    databases_data = MySqlSchemaCollectorLegacy({}, check, check._config)
    with (
        mock.patch('time.time', side_effect=[0, 0]),
        mock.patch('datadog_checks.mysql.schemas_legacy.MySqlSchemaCollectorLegacy._get_tables', return_value=[1, 2]),
        mock.patch('datadog_checks.mysql.schemas_legacy.SubmitData.submit') as mocked_submit,
        mock.patch(
            'datadog_checks.mysql.schemas_legacy.MySqlSchemaCollectorLegacy._get_tables_data',
            return_value=(1000_000, {"name": "my_table"}),
        ),
    ):
        databases_data._fetch_database_data("dummy_cursor", time.time(), "my_db")
        assert mocked_submit.call_count == 2


@pytest.mark.unit
def test_exception_handling_by_do_for_dbs():
    """Test that exceptions during database fetching are handled gracefully"""
    check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    databases_data = MySqlSchemaCollectorLegacy({}, check, check._config)
    with mock.patch(
        'datadog_checks.mysql.schemas_legacy.MySqlSchemaCollectorLegacy._fetch_database_data',
        side_effect=Exception("Can't connect to DB"),
    ):
        databases_data._fetch_for_databases([{"name": "my_db"}], "dummy_cursor")


@pytest.mark.unit
def test_legacy_collector_has_collect_schemas_wrapper():
    """Test that legacy collector has collect_schemas() wrapper method for interface compatibility"""
    check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    legacy_collector = MySqlSchemaCollectorLegacy({}, check, check._config)

    # Verify the wrapper method exists
    assert hasattr(legacy_collector, 'collect_schemas')
    assert callable(legacy_collector.collect_schemas)
