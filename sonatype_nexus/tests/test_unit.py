# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import requests

from datadog_checks.sonatype_nexus import constants
from datadog_checks.sonatype_nexus.check import SonatypeNexusCheck
from datadog_checks.sonatype_nexus.errors import (
    APIError,
    BadRequestError,
    EmptyResponseError,
    InsufficientAPIPermissionError,
    InvalidAPICredentialsError,
    LicenseExpiredError,
    NotFoundError,
    ServerError,
    handle_errors,
)

from .conftest import instance

pytestmark = pytest.mark.unit


class HandleErrorsProbe:
    def __init__(self, check):
        self.log = check.log

    @handle_errors
    def raise_error(self, error):
        raise error


def test_status_number_to_value_maps_each_status_to_alert_type(aggregator):
    # Kills the NumberReplacer mutants at check.py:16 that collapse STATUS_NUMBER_TO_VALUE's
    # duplicate-free {0,1,2} keys into duplicate keys, dropping one of the status mappings.
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    check.ingest_event(status=0, tags=[], message="m0", title="t0", source_type="s0")
    check.ingest_event(status=1, tags=[], message="m1", title="t1", source_type="s1")
    check.ingest_event(status=2, tags=[], message="m2", title="t2", source_type="s2")

    aggregator.assert_event("m0", alert_type="SUCCESS")
    aggregator.assert_event("m1", alert_type="WARNING")
    aggregator.assert_event("m2", alert_type="ERROR")


def test_check_strips_username_and_password_from_instance():
    # Kills the ReplaceOrWithAnd mutants at check.py:24,25 ("X or ''" -> "X and ''").
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    assert check._username == "test_username"
    assert check._password == "test_password"


def test_generate_and_yield_status_metrics_emits_gauge_for_present_keys(mock_http_response, aggregator):
    # Kills the ZeroIterationForLoop mutant at check.py:47, the AddNot mutant at check.py:48,
    # and every ReplaceBinaryOperator_Add_* mutant at check.py:52 (base tags + custom tags).
    status_response_data = {"Scheduler": {"healthy": True}}
    mock_http_response(status_code=200, json_data=status_response_data)
    check_instance = {**instance, "tags": ["sample_tag:sample_value"]}
    check = SonatypeNexusCheck("sonatype_nexus", {}, [check_instance])

    check.generate_and_yield_status_metrics()

    aggregator.assert_metric(
        "sonatype_nexus.status.scheduler_health",
        value=1.0,
        tags=["sonatype_host:None", "sample_tag:sample_value"],
    )


def test_generate_and_yield_analytics_metrics_processes_metric_configs(mock_http_response, aggregator):
    # Kills the ZeroIterationForLoop mutant at check.py:64 that skips METRIC_CONFIGS entirely.
    analytics_response_data = {
        "gauges": {
            "jvm.memory.heap.used": {"value": 123456789},
            "nexus.analytics.bytes_transferred_by_format": {"value": []},
            "nexus.analytics.blobstore_type_counts": {"value": {}},
        }
    }
    mock_http_response(status_code=200, json_data=analytics_response_data)
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    check.generate_and_yield_analytics_metrics()

    aggregator.assert_metric("sonatype_nexus.analytics.jvm.heap_memory_used", value=123456789)


def test_extract_ip_from_url_returns_only_the_captured_ip_group():
    # Kills the NumberReplacer mutants at check.py:38 (match.group(1) -> group(0)/group(2)).
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
    check._server_url = "http://127.0.0.1:8081"

    assert check.extract_ip_from_url() == "127.0.0.1"


def test_generate_and_yield_status_metrics_handles_invalid_json(mock_http_response):
    # Kills the ExceptionReplacer at check.py:44 that disables the JSONDecodeError catch.
    mock_http_response(status_code=200, content="not valid json")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    result = check.generate_and_yield_status_metrics()

    assert result["message"] == "Can't decode API response to json"


def test_generate_and_yield_analytics_metrics_handles_invalid_json(mock_http_response):
    # Kills the ExceptionReplacer at check.py:60 that disables the JSONDecodeError catch.
    mock_http_response(status_code=200, content="not valid json")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    result = check.generate_and_yield_analytics_metrics()

    assert result["message"] == "Can't decode API response to json"


def test_generate_and_yield_analytics_metrics_processes_format_type_configs(mock_http_response, aggregator):
    # Kills the ZeroIterationForLoop mutant at check.py:67 that skips METRIC_CONFIGS_BY_FORMAT_TYPE.
    analytics_response_data = {
        "gauges": {
            "nexus.analytics.bytes_transferred_by_format": {"value": [{"maven": {"bytes_uploaded": 100}}]},
            "nexus.analytics.blobstore_type_counts": {"value": {}},
        }
    }
    mock_http_response(status_code=200, json_data=analytics_response_data)
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    check.generate_and_yield_analytics_metrics()

    aggregator.assert_metric("sonatype_nexus.analytics.uploaded_bytes_by_format", value=100)


def test_generate_and_yield_analytics_metrics_wraps_missing_key_error(mock_http_response):
    # Kills the ExceptionReplacer at check.py:70 that disables the KeyError catch/re-raise.
    mock_http_response(status_code=200, json_data={"gauges": {}})
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    with pytest.raises(KeyError, match="Expected key"):
        check.generate_and_yield_analytics_metrics()


def test_create_metric_for_configs_list_with_tags(aggregator):
    # Kills the ZeroIterationForLoop mutants at check.py:84,86 and every ReplaceBinaryOperator_Add_*
    # mutant at check.py:88 (base_tags + tag_list would raise TypeError for any other list operator).
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
    metric_data = {"value": [{"type": "npm", "blob_count": 42}]}
    metric_name = "analytics.blob_store.blobcount_by_type"

    check.create_metric_for_configs(metric_data, metric_name)

    aggregator.assert_metric(
        f"sonatype_nexus.{metric_name}",
        value=42,
        tags=["sonatype_host:None", "type:npm"],
    )


def test_create_metric_for_configs_list_missing_value_key_defaults_to_zero(aggregator):
    # Kills the NumberReplacer mutants at check.py:88 (default 0 -> 1/-1).
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
    metric_data = {"value": [{"type": "npm"}]}
    metric_name = "analytics.blob_store.blobcount_by_type"

    check.create_metric_for_configs(metric_data, metric_name)

    aggregator.assert_metric(f"sonatype_nexus.{metric_name}", value=0)


def test_create_metric_for_configs_dict_missing_value_key_defaults_to_zero(aggregator):
    # Kills the NumberReplacer mutants at check.py:92 (default 0 -> 1/-1).
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
    metric_data = {"value": {}}
    metric_name = "analytics.malicious_risk_on_disk"

    check.create_metric_for_configs(metric_data, metric_name)

    aggregator.assert_metric(f"sonatype_nexus.{metric_name}", value=0)


def test_create_metric_for_configs_by_format_type_list_missing_value_key_defaults_to_zero(aggregator):
    # Kills the NumberReplacer mutants at check.py:101 (default 0 -> 1/-1).
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
    metric_name = "analytics.uploaded_bytes_by_format"
    metric_info = constants.METRIC_CONFIGS_BY_FORMAT_TYPE[metric_name]
    metric_data = [{"maven": {}}]

    check.create_metric_for_configs_by_format_type(metric_data, metric_name, metric_info)

    aggregator.assert_metric(f"sonatype_nexus.{metric_name}", value=0)


def test_create_metric_for_configs_by_format_type_dict_branch_iterates_all_entries(aggregator):
    # Kills the ZeroIterationForLoop mutant at check.py:104 that skips the dict branch entirely.
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
    metric_name = "analytics.blob_store.count_by_type"
    metric_info = constants.METRIC_CONFIGS_BY_FORMAT_TYPE[metric_name]
    metric_data = {"npm": 7}

    check.create_metric_for_configs_by_format_type(metric_data, metric_name, metric_info)

    aggregator.assert_metric(f"sonatype_nexus.{metric_name}", value=7)


def test_call_api_200_ingests_success_event(mock_http_response, aggregator):
    # Kills the ReplaceComparisonOperator/AddNot/NumberReplacer mutants at api_client.py:37
    # and the NumberReplacer mutant at api_client.py:40 (status=0 -> 1).
    mock_http_response(status_code=200, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    response = check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")

    assert response.status_code == 200
    aggregator.assert_event("Successfully called the Sonatype Nexus API.", alert_type="SUCCESS")


def test_call_api_200_boundary_below_no_success_event(mock_http_response, aggregator):
    # Kills the ReplaceComparisonOperator_Eq_LtE mutant at api_client.py:37 (200 <= 200 vs ==).
    mock_http_response(status_code=150, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    with pytest.raises(APIError):
        check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")

    aggregator.assert_event("Successfully called the Sonatype Nexus API.", count=0)


def test_call_api_200_boundary_above_no_success_event(mock_http_response, aggregator):
    # Kills the ReplaceComparisonOperator_Eq_GtE mutant at api_client.py:37 (200 >= 200 vs ==).
    mock_http_response(status_code=250, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    response = check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")

    assert response.status_code == 250
    aggregator.assert_event("Successfully called the Sonatype Nexus API.", count=0)


def test_call_api_401_ingests_error_event(mock_http_response, aggregator):
    # Kills the ReplaceComparisonOperator/AddNot/NumberReplacer mutants at api_client.py:46
    # and the NumberReplacer mutant at api_client.py:51 (status=2 -> 1).
    mock_http_response(status_code=401, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    with pytest.raises(InvalidAPICredentialsError):
        check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")

    aggregator.assert_event(
        "Error occurred with provided Sonatype Nexus credentials. Please check logs for more details.",
        alert_type="ERROR",
    )


@pytest.mark.parametrize("status_code", [380, 420])
def test_call_api_401_comparison_boundaries_do_not_trigger_credentials_event(mock_http_response, aggregator, status_code):
    # Kills the ReplaceComparisonOperator_Eq_LtE/_Eq_GtE mutants at api_client.py:46.
    mock_http_response(status_code=status_code, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    with pytest.raises(APIError):
        check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")

    aggregator.assert_event(
        "Error occurred with provided Sonatype Nexus credentials. Please check logs for more details.",
        count=0,
    )


def test_call_api_402_ingests_license_event(mock_http_response, aggregator):
    # Kills the ReplaceComparisonOperator/AddNot/NumberReplacer mutants at api_client.py:57
    # and the NumberReplacer mutant at api_client.py:60 (status=2 -> 1).
    mock_http_response(status_code=402, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    with pytest.raises(LicenseExpiredError):
        check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")

    aggregator.assert_event(
        "Invalid Sonatype Nexus license, access to the requested resource requires payment.",
        alert_type="ERROR",
    )


@pytest.mark.parametrize("status_code", [385, 425])
def test_call_api_402_comparison_boundaries_do_not_trigger_license_event(mock_http_response, aggregator, status_code):
    # Kills the ReplaceComparisonOperator_Eq_LtE/_Eq_GtE mutants at api_client.py:57.
    mock_http_response(status_code=status_code, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    with pytest.raises(APIError):
        check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")

    aggregator.assert_event(
        "Invalid Sonatype Nexus license, access to the requested resource requires payment.",
        count=0,
    )


def test_call_api_403_ingests_permission_event(mock_http_response, aggregator):
    # Kills the ReplaceComparisonOperator/AddNot/NumberReplacer mutants at api_client.py:66
    # and the NumberReplacer mutant at api_client.py:71 (status=2 -> 1).
    mock_http_response(status_code=403, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    with pytest.raises(InsufficientAPIPermissionError):
        check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")

    aggregator.assert_event(
        "Insufficient permissions to call the Sonatype Nexus API. Please check logs for more details.",
        alert_type="ERROR",
    )


@pytest.mark.parametrize("status_code", [390, 430])
def test_call_api_403_comparison_boundaries_do_not_trigger_permission_event(mock_http_response, aggregator, status_code):
    # Kills the ReplaceComparisonOperator_Eq_LtE/_Eq_GtE mutants at api_client.py:66.
    mock_http_response(status_code=status_code, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    with pytest.raises(APIError):
        check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")

    aggregator.assert_event(
        "Insufficient permissions to call the Sonatype Nexus API. Please check logs for more details.",
        count=0,
    )


def test_call_api_swallows_transport_exception_and_returns_empty_response_error(mocker):
    # Kills the ExceptionReplacer at api_client.py:79 that disables the broad Exception catch:
    # without it, the ConnectionError itself reaches handle_errors instead of being swallowed
    # into a None response, so the wrapped message would differ from "Unexpected error occurred.".
    mocker.patch("requests.Session.get", side_effect=requests.exceptions.ConnectionError("boom"))
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    with pytest.raises(APIError, match="Unexpected error occurred.") as excinfo:
        check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")

    assert isinstance(excinfo.value.__cause__, EmptyResponseError)


def test_status_code_199_is_not_successful(mock_http_response):
    # Kills the NumberReplacer mutant at errors.py:55 (range(200, 299) -> range(199, 299)).
    mock_http_response(status_code=199, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    with pytest.raises(APIError):
        check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")


def test_status_code_298_is_successful(mock_http_response):
    # Kills the NumberReplacer mutant at errors.py:55 (range(200, 299) -> range(200, 298)).
    mock_http_response(status_code=298, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    response = check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")

    assert response.status_code == 298


def test_status_code_299_is_not_successful(mock_http_response):
    # Kills the NumberReplacer mutant at errors.py:55 (range(200, 299) -> range(200, 300)).
    mock_http_response(status_code=299, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    with pytest.raises(APIError):
        check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")


@pytest.mark.parametrize("status_code", [502, 503, 504])
def test_server_error_status_codes_raise_server_error(mock_http_response, status_code):
    # Kills the NumberReplacer mutants at errors.py:69 that drop 502/503/504 from the server-error list.
    mock_http_response(status_code=status_code, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    with pytest.raises(ServerError):
        check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")


@pytest.mark.parametrize(
    "status_code, expected_exception",
    [
        (400, BadRequestError),
        (401, InvalidAPICredentialsError),
        (402, LicenseExpiredError),
        (403, InsufficientAPIPermissionError),
        (404, NotFoundError),
        (500, ServerError),
    ],
)
def test_handle_errors_raises_specific_exception_type(mock_http_response, status_code, expected_exception):
    # Kills the ExceptionReplacer mutants at errors.py:95,99,103,107,111,115 that disable each
    # specific except clause, which would let the status code fall through to a generic APIError.
    mock_http_response(status_code=status_code, content="")
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    with pytest.raises(expected_exception):
        check.sonatype_nexus_client.call_sonatype_nexus_api("https://example.com/x")


@pytest.mark.parametrize(
    "raised, expected_message",
    [
        (requests.exceptions.Timeout(), "Timeout while requesting data from the API."),
        (requests.exceptions.ConnectionError(), "Error while connecting to the API."),
        (requests.exceptions.RequestException(), "General request error occurred."),
        (ValueError("boom"), "Unexpected error occurred."),
    ],
)
def test_handle_errors_wraps_transport_and_unexpected_exceptions(raised, expected_message):
    # Kills the ExceptionReplacer mutants at errors.py:83,87,91,119 that disable the Timeout,
    # ConnectionError, RequestException and catch-all Exception clauses.
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
    probe = HandleErrorsProbe(check)

    with pytest.raises(APIError, match=expected_message):
        probe.raise_error(raised)
