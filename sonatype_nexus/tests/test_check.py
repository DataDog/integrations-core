# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import unittest
from unittest.mock import MagicMock, call, patch

import pytest
import requests
from datadog_checks.sonatype_nexus import constants
from datadog_checks.sonatype_nexus.check import SonatypeNexusCheck
from datadog_checks.sonatype_nexus.constants import STATUS_METRICS_MAP

SONATYPE_HOST = "sonatype_host:127.0.0.1"


@pytest.mark.e2e
@patch("datadog_checks.sonatype_nexus.check.SonatypeNexusCheck.extract_ip_from_url")
@patch("datadog_checks.sonatype_nexus.check.SonatypeNexusClient")
def test_success(mock_client_class, mock_extract_ip):
    check = SonatypeNexusCheck("sonatype_nexus", {}, [{}])
    check.gauge = MagicMock()
    check.log = MagicMock()
    mock_extract_ip.return_value = "127.0.0.1"
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = {key: {"healthy": 1} for key in STATUS_METRICS_MAP.keys()}
    mock_client.call_sonatype_nexus_api.return_value.json.return_value = mock_response
    check.sonatype_nexus_client = mock_client

    check.generate_and_yield_status_metrics()

    expected_calls = [
        call(metric_name, 1, [SONATYPE_HOST], hostname=None) for metric_name in STATUS_METRICS_MAP.values()
    ]
    check.gauge.assert_has_calls(expected_calls, any_order=True)
    assert check.gauge.call_count == len(STATUS_METRICS_MAP)


@patch("datadog_checks.sonatype_nexus.check.SonatypeNexusClient")
def test_json_decode_error(mock_client_class):
    check = SonatypeNexusCheck("sonatype_nexus", {}, [{}])
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.call_sonatype_nexus_api.return_value.json.side_effect = requests.exceptions.JSONDecodeError(
        "Test error", "", 0
    )
    check.sonatype_nexus_client = mock_client
    result = check.generate_and_yield_status_metrics()
    assert result == {
        "message": "Can't decode API response to json",
        "error": "Test error: line 1 column 1 (char 0)",
    }


def setup_sonatype_nexus_check():
    with patch("datadog_checks.sonatype_nexus.check.SonatypeNexusCheck") as mock_check:
        check = mock_check.return_value
        check.sonatype_nexus_client = MagicMock()
        check.create_metric_for_configs = MagicMock()
        check.create_metric_for_configs_by_format_type = MagicMock()
        return check


@patch("datadog_checks.sonatype_nexus.check.SonatypeNexusClient")
def test_generate_and_yield_analytics_metrics_success(mock_client):
    check = setup_sonatype_nexus_check()
    mock_client.call_sonatype_nexus_api.return_value.json.return_value = {
        "gauges": {"metric_key1": {"value": 1}, "metric_key2": {"value": 2}}
    }
    constants.METRIC_CONFIGS = {
        "metric_name1": {"metric_key": "metric_key1"},
        "metric_name2": {"metric_key": "metric_key2"},
    }
    constants.METRIC_CONFIGS_BY_FORMAT_TYPE = {"metric_name3": {"metric_key": "metric_key3", "value_key": "value"}}
    check.generate_and_yield_analytics_metrics()
    assert check.create_metric_for_configs.call_count == 0


@patch("datadog_checks.sonatype_nexus.check.SonatypeNexusClient")
def test_generate_and_yield_analytics_metrics_missing_metric_key(mock_client):
    check = setup_sonatype_nexus_check()
    mock_client.call_sonatype_nexus_api.return_value.json.return_value = {"gauges": {}}
    constants.METRIC_CONFIGS = {"metric_name1": {"metric_key": "metric_key1"}}
    check.generate_and_yield_analytics_metrics()
    check.create_metric_for_configs.assert_not_called()


@patch("datadog_checks.sonatype_nexus.check.SonatypeNexusClient")
def test_generate_and_yield_analytics_metrics_empty_response_json(mock_client):
    check = setup_sonatype_nexus_check()
    mock_client.call_sonatype_nexus_api.return_value.json.return_value = {}
    constants.METRIC_CONFIGS = {"metric_name1": {"metric_key": "metric_key1"}}
    check.generate_and_yield_analytics_metrics()
    check.create_metric_for_configs.assert_not_called()


@patch("datadog_checks.sonatype_nexus.check.SonatypeNexusClient")
def test_generate_and_yield_analytics_metrics_none_response(mock_client):
    check = setup_sonatype_nexus_check()
    mock_client.call_sonatype_nexus_api.return_value = None
    constants.METRIC_CONFIGS = {"metric_name1": {"metric_key": "metric_key1"}}
    check.generate_and_yield_analytics_metrics()
    check.create_metric_for_configs.assert_not_called()


@patch("datadog_checks.sonatype_nexus.check.SonatypeNexusCheck.process_metrics")
def test_metric_key_present(mock_process_metrics):
    response_json = {"metric_key": "value"}
    mock_process_metrics.return_value = response_json["metric_key"]
    result = mock_process_metrics("metric_key", response_json)
    assert result == "value"
    mock_process_metrics.assert_called_once_with("metric_key", response_json)


@patch("datadog_checks.sonatype_nexus.check.SonatypeNexusCheck.process_metrics")
def test_metric_key_not_present(mock_process_metrics):
    response_json = {"other_key": "value"}
    mock_process_metrics.return_value = None
    result = mock_process_metrics("metric_key", response_json)
    assert result is None
    mock_process_metrics.assert_called_once_with("metric_key", response_json)


@patch("datadog_checks.sonatype_nexus.check.SonatypeNexusCheck.process_metrics")
def test_empty_response_json(mock_process_metrics):
    response_json = {}
    mock_process_metrics.return_value = None
    result = mock_process_metrics("metric_key", response_json)
    assert result is None
    mock_process_metrics.assert_called_once_with("metric_key", response_json)


@patch("datadog_checks.sonatype_nexus.check.SonatypeNexusCheck.process_metrics")
def test_response_json_with_different_data_type(mock_process_metrics):
    response_json = [1, 2, 3]
    mock_process_metrics.return_value = None
    result = mock_process_metrics("metric_key", response_json)
    assert result is None
    mock_process_metrics.assert_called_once_with("metric_key", response_json)


def test_list_value():
    check = SonatypeNexusCheck("sonatype_nexus", {}, [{}])
    check.gauge = MagicMock()
    check.extract_ip_from_url = MagicMock(return_value="127.0.0.1")

    metric_data = {"value": [{"tag_key": "tag_value", "value_key": 10}]}
    config = {"tag_key": ["tag_key"], "value_key": "value_key"}
    constants.METRIC_CONFIGS = {"metric_name": config}

    check.create_metric_for_configs(metric_data, "metric_name")
    check.gauge.assert_called_once_with("metric_name", 10, [SONATYPE_HOST, "tag_key:tag_value"], hostname=None)


def test_int_value():
    check = SonatypeNexusCheck("sonatype_nexus", {}, [{}])
    check.gauge = MagicMock()
    check.extract_ip_from_url = MagicMock(return_value="127.0.0.1")

    metric_data = {"value": 10}
    config = {"tag_key": [], "value_key": ""}
    constants.METRIC_CONFIGS = {"metric_name": config}

    check.create_metric_for_configs(metric_data, "metric_name")
    check.gauge.assert_called_once_with("metric_name", 10, [SONATYPE_HOST], hostname=None)


def test_dict_value():
    check = SonatypeNexusCheck("sonatype_nexus", {}, [{}])
    check.gauge = MagicMock()
    check.extract_ip_from_url = MagicMock(return_value="127.0.0.1")

    metric_data = {"value": {"value_key": 10}}
    config = {"tag_key": [], "value_key": "value_key"}
    constants.METRIC_CONFIGS = {"metric_name": config}

    check.create_metric_for_configs(metric_data, "metric_name")
    check.gauge.assert_called_once_with("metric_name", 10, [SONATYPE_HOST], hostname=None)


def test_missing_value_key():
    check = SonatypeNexusCheck("sonatype_nexus", {}, [{}])
    check.gauge = MagicMock()
    check.extract_ip_from_url = MagicMock(return_value="127.0.0.1")

    metric_data = {}
    config = {"tag_key": [], "value_key": "value_key"}
    constants.METRIC_CONFIGS = {"metric_name": config}

    check.create_metric_for_configs(metric_data, "metric_name")
    check.gauge.assert_not_called()


def test_metric_data_as_list():
    check = MagicMock()
    check.extract_ip_from_url.return_value = "127.0.0.1"
    metric_data = [
        {"format_type1": {"value_key": 10}},
        {"format_type2": {"value_key": 20}},
    ]
    metric_name = "metric_name"
    metric_info = {"value_key": "value_key"}

    create_metric_for_configs_by_format_type(check, metric_data, metric_name, metric_info)

    check.ingest_metric.assert_any_call([SONATYPE_HOST], "format_type1", metric_info, metric_name, 10)
    check.ingest_metric.assert_any_call([SONATYPE_HOST], "format_type2", metric_info, metric_name, 20)
    assert check.ingest_metric.call_count == 2


def test_metric_data_as_dict():
    check = MagicMock()
    check.extract_ip_from_url.return_value = "127.0.0.1"
    metric_data = {"format_type1": 10, "format_type2": 20}
    metric_name = "metric_name"
    metric_info = {"value_key": "value_key"}

    create_metric_for_configs_by_format_type(check, metric_data, metric_name, metric_info)

    check.ingest_metric.assert_any_call([SONATYPE_HOST], "format_type1", metric_info, metric_name, 10)
    check.ingest_metric.assert_any_call([SONATYPE_HOST], "format_type2", metric_info, metric_name, 20)
    assert check.ingest_metric.call_count == 2


def test_metric_data_as_empty_list():
    check = MagicMock()
    metric_data = []
    metric_name = "metric_name"
    metric_info = {"value_key": "value_key"}

    create_metric_for_configs_by_format_type(check, metric_data, metric_name, metric_info)

    check.ingest_metric.assert_not_called()


def test_metric_data_as_empty_dict():
    check = MagicMock()
    metric_data = {}
    metric_name = "metric_name"
    metric_info = {"value_key": "value_key"}

    create_metric_for_configs_by_format_type(check, metric_data, metric_name, metric_info)

    check.ingest_metric.assert_not_called()


def test_metric_data_as_none():
    check = MagicMock()
    metric_data = None
    metric_name = "metric_name"
    metric_info = {"value_key": "value_key"}

    create_metric_for_configs_by_format_type(check, metric_data, metric_name, metric_info)

    check.ingest_metric.assert_not_called()


def create_metric_for_configs_by_format_type(self, metric_data, metric_name, metric_info):
    base_tag = [f"sonatype_host:{self.extract_ip_from_url()}"]

    if isinstance(metric_data, list):
        for item in metric_data:
            for format_type, data in item.items():
                self.ingest_metric(
                    base_tag,
                    format_type,
                    metric_info,
                    metric_name,
                    data[metric_info["value_key"]],
                )
    elif isinstance(metric_data, dict):
        for format_type, metric_value in metric_data.items():
            self.ingest_metric(base_tag, format_type, metric_info, metric_name, metric_value)


class TestIngestMetric(unittest.TestCase):
    def setUp(self):
        self.check = SonatypeNexusCheck("sonatype_nexus", {}, [{}])
        self.check.gauge = MagicMock()

    def test_valid_input(self):
        base_tag = [SONATYPE_HOST]
        format_type = "format_type"
        metric_info = {"tag_key": "tag_key"}
        metric_name = "metric_name"
        value = 10
        self.check.ingest_metric(base_tag, format_type, metric_info, metric_name, value)
        self.check.gauge.assert_called_once_with(
            metric_name,
            10,
            base_tag + [f"{metric_info['tag_key']}:{format_type}"],
            hostname=None,
        )

    def test_non_integer_value(self):
        base_tag = [SONATYPE_HOST]
        format_type = "format_type"
        metric_info = {"tag_key": "tag_key"}
        metric_name = "metric_name"
        value = "non-integer"
        with self.assertRaises(ValueError):
            self.check.ingest_metric(base_tag, format_type, metric_info, metric_name, value)

    def test_missing_tag_key(self):
        base_tag = [SONATYPE_HOST]
        format_type = "format_type"
        metric_info = {}
        metric_name = "metric_name"
        value = 10
        with self.assertRaises(KeyError):
            self.check.ingest_metric(base_tag, format_type, metric_info, metric_name, value)


def test_service_check_and_event_with_all_required_arguments():
    check = SonatypeNexusCheck("sonatype_nexus", {}, [{}])
    check.service_check = MagicMock()
    check.event = MagicMock()
    check.extract_ip_from_url = MagicMock(return_value="127.0.0.1")

    with patch("datadog_checks.sonatype_nexus.check.STATUS_NUMBER_TO_VALUE") as mock_status_number_to_value:
        mock_status_number_to_value.get.return_value = "OK"
        check.ingest_event(
            status=0,
            tags=["tag1", "tag2"],
            message="Test message",
            title="Test title",
            source_type="Test source type",
        )
        check.event.assert_called_once()


def test_service_check_and_event_with_none_values_for_tags_and_message():
    check = SonatypeNexusCheck("sonatype_nexus", {}, [{}])
    check.service_check = MagicMock()
    check.event = MagicMock()
    check.extract_ip_from_url = MagicMock(return_value="127.0.0.1")
    check.ingest_event(
        status=0,
        tags=None,
        message=None,
        title="Test title",
        source_type="Test source type",
    )
    check.event.assert_called_once()


@pytest.fixture
def check():
    return SonatypeNexusCheck("sonatype_nexus", {}, [{}])


def test_valid_url_with_ip(check):
    check._server_url = "https://0.0.0.0"
    assert check.extract_ip_from_url() == "0.0.0.0"


def test_valid_url_with_domain(check):
    check._server_url = "https://example.com"
    assert check.extract_ip_from_url() is None


def test_invalid_url(check):
    check._server_url = " invalid url "
    assert check.extract_ip_from_url() is None


def test_url_with_no_ip_or_domain(check):
    check._server_url = "https://"
    assert check.extract_ip_from_url() is None


def test_url_with_multiple_ips(check):
    check._server_url = "https://0.0.0.0,0.0.0.2"
    assert check.extract_ip_from_url() == "0.0.0.0"
