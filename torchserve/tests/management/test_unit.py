# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics

from ..conftest import mock_http_responses
from .common import METRICS

pytestmark = pytest.mark.unit


def test_check(dd_run_check, aggregator, check, mocked_management_instance, mocker):
    mocker.patch('requests.get', wraps=mock_http_responses())
    dd_run_check(check(mocked_management_instance))

    for metric in METRICS:
        aggregator.assert_metric(
            metric["name"],
            value=metric.get("value"),
            tags=metric.get("tags", []) + [f"management_api_url:{mocked_management_instance['management_api_url']}"],
            at_least=metric.get("at_least", 1),
            count=metric.get("count", 1),
        )

    aggregator.assert_service_check("torchserve.management_api.health", AgentCheck.OK)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_no_duplicate_all()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    assert len(aggregator.events) == 0


def test_check_fails_on_one_model(dd_run_check, aggregator, check, mocked_management_instance, mocker):
    def custom_mock_http_responses(url, **_params):
        if url in (
            'http://torchserve:8081/models/linear_regression_1_1/all',
            'http://torchserve:8081/models/linear_regression_2_2/all',
        ):
            return MockResponse(status_code=500)

        return mock_http_responses()(url)

    mocker.patch('requests.get', wraps=custom_mock_http_responses)
    dd_run_check(check(mocked_management_instance))

    # We should not get anything for these models
    aggregator.assert_metric(
        "torchserve.management_api.model.versions",
        tags=[
            'model_name:linear_regression_1_1',
            f"management_api_url:{mocked_management_instance['management_api_url']}",
        ],
        count=0,
    )
    aggregator.assert_metric(
        "torchserve.management_api.model.versions",
        tags=[
            'model_name:linear_regression_2_2',
            f"management_api_url:{mocked_management_instance['management_api_url']}",
        ],
        count=0,
    )

    # Assert we still have the other models
    aggregator.assert_metric(
        "torchserve.management_api.model.versions",
        value=3,
        tags=[
            'model_name:linear_regression_1_2',
            f"management_api_url:{mocked_management_instance['management_api_url']}",
        ],
    )
    aggregator.assert_metric(
        "torchserve.management_api.model.versions",
        value=1,
        tags=[
            'model_name:linear_regression_2_3',
            f"management_api_url:{mocked_management_instance['management_api_url']}",
        ],
    )
    aggregator.assert_metric(
        "torchserve.management_api.model.versions",
        value=1,
        tags=[
            'model_name:linear_regression_3_2',
            f"management_api_url:{mocked_management_instance['management_api_url']}",
        ],
    )

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    assert len(aggregator.events) == 0


@pytest.mark.parametrize(
    'include, exclude, limit, expected_models',
    [
        pytest.param(
            [".*"],
            None,
            None,
            [
                "linear_regression_1_1",
                "linear_regression_1_2",
                "linear_regression_2_2",
                "linear_regression_2_3",
                "linear_regression_3_2",
            ],
            id="get everything",
        ),
        pytest.param(
            ["linear_regression_1.*"],
            None,
            None,
            ["linear_regression_1_1", "linear_regression_1_2"],
            id="only 1_",
        ),
        pytest.param(
            ["linear_regression_1.*", "linear_regression_2.*"],
            None,
            None,
            ["linear_regression_1_1", "linear_regression_1_2", "linear_regression_2_2", "linear_regression_2_3"],
            id="only 1_ and 2_",
        ),
        pytest.param(
            [".*"],
            ["linear_regression_1.*"],
            None,
            ["linear_regression_2_2", "linear_regression_2_3", "linear_regression_3_2"],
            id="not 1_",
        ),
        pytest.param(
            [".*"],
            ["linear_regression_1.*", "linear_regression_2.*"],
            None,
            ["linear_regression_3_2"],
            id="not 1_ nor 2",
        ),
        pytest.param(
            [".*"],
            None,
            2,
            ["linear_regression_1_1", "linear_regression_1_2"],
            id="only the first two",
        ),
        pytest.param(
            None,
            [".*"],
            None,
            [],
            id="exclude everything",
        ),
    ],
)
def test_check_with_discovery(
    dd_run_check, aggregator, check, mocked_management_instance, mocker, include, exclude, limit, expected_models
):
    mocker.patch('requests.get', wraps=mock_http_responses())
    mocked_management_instance["limit"] = limit
    mocked_management_instance["exclude"] = exclude
    mocked_management_instance["include"] = include
    dd_run_check(check(mocked_management_instance))

    for metric in METRICS:
        aggregator.assert_metric(
            metric["name"],
            value=metric.get("value"),
            tags=metric.get("tags", []) + [f"management_api_url:{mocked_management_instance['management_api_url']}"],
            count=1 if metric_should_be_exposed(metric, expected_models) else 0,
        )

    aggregator.assert_service_check("torchserve.management_api.health", AgentCheck.OK)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_no_duplicate_all()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    assert len(aggregator.events) == 0


def metric_should_be_exposed(metric, expected_models):
    # always exposed
    if metric["name"] == "torchserve.management_api.models":
        return True

    for tag in metric.get("tags", []):
        key, value = tag.split(":")
        if key == "model_name":
            return value in expected_models

    return False


@pytest.mark.parametrize(
    'new_response, expected_events',
    [
        pytest.param(
            "management/models.json",
            [],
            id="no events",
        ),
        pytest.param(
            "management/events/models_with_3_3.json",
            [
                {
                    "type": "torchserve.management_api.model_added",
                    "title": "A new model has been added",
                    "message": "The model [linear_regression_3_3] has been added with the "
                    "file [linear_regression_3_3.mar].",
                    "tags": ['model_name:linear_regression_3_3'],
                },
            ],
            id="new model",
        ),
        pytest.param(
            "management/events/models_with_v1_as_default_for_1_1.json",
            [
                {
                    "type": "torchserve.management_api.default_version_changed",
                    "title": 'A new default version has been set for a model',
                    "message": 'A new default version has been set for the model [linear_regression_1_2], '
                    'from file [linear_regression_1_2_v3.mar] to file [linear_regression_1_2_v1.mar].',
                    "tags": ['model_name:linear_regression_1_2'],
                },
            ],
            id="new version set",
        ),
        pytest.param(
            "management/events/models_without_3_2.json",
            [
                {
                    "type": "torchserve.management_api.model_removed",
                    "title": "A model has been removed",
                    "message": "The model [linear_regression_3_2] has been removed.",
                    "tags": ['model_name:linear_regression_3_2'],
                },
            ],
            id="one model removed",
        ),
        pytest.param(
            "management/events/models_without_2_2_with_3_3_and_1_2_v1.json",
            [
                {
                    "type": "torchserve.management_api.default_version_changed",
                    "title": 'A new default version has been set for a model',
                    "message": 'A new default version has been set for the model [linear_regression_1_2], '
                    'from file [linear_regression_1_2_v3.mar] to file [linear_regression_1_2_v1.mar].',
                    "tags": ['model_name:linear_regression_1_2'],
                },
                {
                    "type": "torchserve.management_api.model_removed",
                    "title": "A model has been removed",
                    "message": "The model [linear_regression_2_2] has been removed.",
                    "tags": ['model_name:linear_regression_2_2'],
                },
                {
                    "type": "torchserve.management_api.model_added",
                    "title": "A new model has been added",
                    "message": "The model [linear_regression_3_3] has been added with the file "
                    "[linear_regression_3_3.mar].",
                    "tags": ['model_name:linear_regression_3_3'],
                },
            ],
            id="one model removed, one model added and one version updated",
        ),
        pytest.param(
            "management/events/models_all_dropped.json",
            [
                {
                    "type": "torchserve.management_api.model_removed",
                    "title": "A model has been removed",
                    "message": "The model [linear_regression_1_1] has been removed.",
                    "tags": ['model_name:linear_regression_1_1'],
                },
                {
                    "type": "torchserve.management_api.model_removed",
                    "title": "A model has been removed",
                    "message": "The model [linear_regression_1_2] has been removed.",
                    "tags": ['model_name:linear_regression_1_2'],
                },
                {
                    "type": "torchserve.management_api.model_removed",
                    "title": "A model has been removed",
                    "message": "The model [linear_regression_2_2] has been removed.",
                    "tags": ['model_name:linear_regression_2_2'],
                },
                {
                    "type": "torchserve.management_api.model_removed",
                    "title": "A model has been removed",
                    "message": "The model [linear_regression_2_3] has been removed.",
                    "tags": ['model_name:linear_regression_2_3'],
                },
                {
                    "type": "torchserve.management_api.model_removed",
                    "title": "A model has been removed",
                    "message": "The model [linear_regression_3_2] has been removed.",
                    "tags": ['model_name:linear_regression_3_2'],
                },
            ],
            id="all models removed",
        ),
    ],
)
def test_check_with_events(
    dd_run_check, datadog_agent, aggregator, check, mocked_management_instance, mocker, new_response, expected_events
):
    # We generate a cache to save the models, so clear it to make sure we won't get the data from a previous test.
    datadog_agent.reset()

    check_instance = check(mocked_management_instance)
    mocker.patch('requests.get', wraps=mock_http_responses())
    dd_run_check(check_instance)
    dd_run_check(check_instance)

    assert len(aggregator.events) == 0

    mocker.patch('requests.get', wraps=mock_http_responses(new_response))
    dd_run_check(check_instance)

    for expected_event, actual_event in zip(expected_events, aggregator.events, strict=True):
        assert "timestamp" in actual_event and actual_event["timestamp"]
        assert "host" in actual_event and actual_event["host"]
        assert actual_event["alert_type"] == "info"
        assert actual_event["source_type_name"] == "torchserve"

        assert actual_event["event_type"] == expected_event["type"]
        assert actual_event["msg_title"] == expected_event["title"]
        assert actual_event["msg_text"] == expected_event["message"]
        assert (
            actual_event["tags"]
            == [f"management_api_url:{mocked_management_instance['management_api_url']}"] + expected_event["tags"]
        )


def test_check_disable_events(dd_run_check, datadog_agent, aggregator, check, mocked_management_instance, mocker):
    # We generate a cache to save the models, so clear it to make sure we won't get the data from a previous test.
    datadog_agent.reset()
    mocked_management_instance["submit_events"] = False

    check_instance = check(mocked_management_instance)
    mocker.patch('requests.get', wraps=mock_http_responses())
    dd_run_check(check_instance)
    dd_run_check(check_instance)

    assert len(aggregator.events) == 0

    mocker.patch('requests.get', wraps=mock_http_responses("management/events/models_all_dropped.json"))
    dd_run_check(check_instance)

    assert len(aggregator.events) == 0
