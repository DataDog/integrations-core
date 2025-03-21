# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock, patch

import pytest

from datadog_checks.base import AgentCheck, ConfigurationError  # noqa: F401
from datadog_checks.silverstripe_cms import SilverstripeCMSCheck, constants
from datadog_checks.silverstripe_cms.database_client import DatabaseClient
from datadog_checks.silverstripe_cms.dataclasses import TableConfig


@pytest.mark.unit
def test_validate_configurations_without_database_type(instance):
    field = "SILVERSTRIPE_DATABASE_TYPE"
    del instance[field]
    check = SilverstripeCMSCheck("silverstripe_cms", {}, [instance])

    with pytest.raises(
        ConfigurationError,
        match=f"'{field}' field is required.",
    ):
        check.validate_configurations()


@pytest.mark.unit
def test_validate_configurations_with_wrong_database_type(instance):
    check = SilverstripeCMSCheck("silverstripe_cms", {}, [instance])

    # with wrong SILVERSTRIPE_DATABASE_TYPE field
    err_message = (
        f"'SILVERSTRIPE_DATABASE_TYPE' must be one of {constants.SUPPORTED_DATABASE_TYPES}. "
        "Please provide a valid SILVERSTRIPE_DATABASE_TYPE."
    )
    with pytest.raises(ConfigurationError) as err:
        check.database_type = "Postgres"
        check.validate_configurations()
        assert str(err) == err_message


@pytest.mark.unit
def test_validate_configurations_with_wrong_database_server_ip(instance):
    check = SilverstripeCMSCheck("silverstripe_cms", {}, [instance])

    err_message = (
        "'SILVERSTRIPE_DATABASE_SERVER_IP' is not valid."
        " Please provide a proper Silverstripe CMS database server IP address with ipv4 protocol."
    )
    with pytest.raises(ConfigurationError, match=err_message):
        check.database_server_ip = "00.10.20"
        check.validate_configurations()


@pytest.mark.unit
def test_validate_configurations_with_wrong_port(instance):
    check = SilverstripeCMSCheck("silverstripe_cms", {}, [instance])

    wrong_port = -10
    err_message = (
        f"'SILVERSTRIPE_DATABASE_PORT' must be a positive integer in range of {constants.MIN_PORT}"
        f" to {constants.MAX_PORT}, got {check.database_port}."
    )
    with pytest.raises(ConfigurationError) as err:
        check.database_port = wrong_port
        check.validate_configurations()
        assert str(err) == err_message


@pytest.mark.unit
def test_validate_configurations_with_wrong_min_collection_interval(instance):
    check = SilverstripeCMSCheck("silverstripe_cms", {}, [instance])

    wrong_interval = -10
    err_message = (
        f"'min_collection_interval' must be a positive integer in range of {constants.MIN_COLLECTION_INTERVAL}"
        f" to {constants.MAX_COLLECTION_INTERVAL}, got {wrong_interval}."
    )
    with pytest.raises(ConfigurationError, match=err_message):
        check.min_collection_interval = wrong_interval
        check.validate_configurations()


@pytest.mark.unit
def test_initialize_db_client(instance):
    check = SilverstripeCMSCheck("silverstripe_cms", {}, [instance])
    check.validate_configurations()
    check.initialize_db_client()

    assert isinstance(check.db_client, DatabaseClient)


@pytest.mark.unit
@patch.object(DatabaseClient, "build_query")
@patch.object(DatabaseClient, "execute_query")
@patch.object(SilverstripeCMSCheck, "ingest_query_result")
def test_metrics_collection_and_ingestion(mock_ingest_query_result, mock_execute_query, mock_build_query, instance):
    check = SilverstripeCMSCheck("silverstripe_cms", {}, [instance])

    check.validate_configurations()
    check.initialize_db_client()
    check.metrics_collection_and_ingestion()

    table_config_mappings = len(constants.METRIC_TO_TABLE_CONFIG_MAPPING)
    query_mappings = len(constants.METRIC_TO_QUERY_MAPPING)
    assert mock_build_query.call_count == table_config_mappings
    assert mock_execute_query.call_count == table_config_mappings + query_mappings
    assert mock_ingest_query_result.call_count == table_config_mappings + query_mappings


@pytest.mark.unit
@patch.object(SilverstripeCMSCheck, "gauge")
def test_ingest_query_result(mock_gauge, instance):
    check = SilverstripeCMSCheck("silverstripe_cms", {}, [instance])

    check.validate_configurations()
    check.initialize_db_client()

    mock_cursor = MagicMock()
    mock_cursor.__iter__.return_value = [
        {"ClassName": "SilverStripe\\ErrorPage\\ErrorPage", "RowCount": 2},
        {"ClassName": "SilverStripe\\CMS\\Model\\RedirectorPage", "RowCount": 3},
        {"ClassName": "SilverStripe\\CMS\\Model\\VirtualPage", "RowCount": 10},
    ]

    check.ingest_query_result(mock_cursor, "pages_live.count")
    assert mock_gauge.call_count == 3


@pytest.mark.unit
def test_extract_metric_tags(instance):
    check = SilverstripeCMSCheck("silverstripe_cms", {}, [instance])

    mock_row_data = {"ClassName": "SilverStripe\\ErrorPage\\ErrorPage", "RowCount": 2, "ID": 1, "FirstName": "john"}
    result = check.get_metric_tags(mock_row_data)
    assert result == ["page_type:error_page", "id:1", "firstname:john"]


@pytest.mark.unit
def test_build_query(instance):
    check = SilverstripeCMSCheck("silverstripe_cms", {}, [instance])
    check.initialize_db_client()
    mock_table_config = TableConfig(name=constants.FILE, conditions=[constants.ANYONE_CAN_VIEW])
    result = check.db_client.build_query(mock_table_config)

    query = 'SELECT `ClassName`, COUNT(*) as `RowCount` FROM `File` WHERE `CanViewType`=\'Anyone\' GROUP BY `ClassName`'
    assert result == query
