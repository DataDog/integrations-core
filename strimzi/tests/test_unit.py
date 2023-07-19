# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.strimzi import StrimziCheck

from .common import (
    CLUSTER_OPERATOR_METRICS,
    MOCKED_CLUSTER_OPERATOR_INSTANCE,
    MOCKED_CLUSTER_OPERATOR_TAG,
    MOCKED_TOPIC_OPERATOR_INSTANCE,
    MOCKED_TOPIC_OPERATOR_TAG,
    MOCKED_USER_OPERATOR_INSTANCE,
    MOCKED_USER_OPERATOR_TAG,
    TOPIC_OPERATOR_METRICS,
    USER_OPERATOR_METRICS,
)
from .conftest import mock_http_responses

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "namespace, instance, metrics, tag",
    [
        (
            "cluster_operator",
            MOCKED_CLUSTER_OPERATOR_INSTANCE,
            CLUSTER_OPERATOR_METRICS,
            MOCKED_CLUSTER_OPERATOR_TAG,
        ),
        (
            "topic_operator",
            MOCKED_TOPIC_OPERATOR_INSTANCE,
            TOPIC_OPERATOR_METRICS,
            MOCKED_TOPIC_OPERATOR_TAG,
        ),
        (
            "user_operator",
            MOCKED_USER_OPERATOR_INSTANCE,
            USER_OPERATOR_METRICS,
            MOCKED_USER_OPERATOR_TAG,
        ),
    ],
)
def test_check_unique_operator(
    dd_run_check,
    aggregator,
    check,
    namespace,
    instance,
    metrics,
    tag,
    mocker,
):
    mocker.patch("requests.get", wraps=mock_http_responses)
    dd_run_check(check(instance))

    for expected_metric in metrics:
        aggregator.assert_metric(expected_metric)
        aggregator.assert_metric_has_tag(expected_metric, tag)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check(
        f"strimzi.{namespace}.openmetrics.health",
        status=StrimziCheck.OK,
        tags=[tag],
        count=1,
    )
    assert len(aggregator.service_check_names) == 1


def test_check_all_operators(dd_run_check, aggregator, check, mocker):
    mocker.patch("requests.get", wraps=mock_http_responses)
    dd_run_check(
        check(
            {
                **MOCKED_CLUSTER_OPERATOR_INSTANCE,
                **MOCKED_TOPIC_OPERATOR_INSTANCE,
                **MOCKED_USER_OPERATOR_INSTANCE,
            }
        )
    )
    for endpoint_metrics in (
        CLUSTER_OPERATOR_METRICS,
        TOPIC_OPERATOR_METRICS,
        USER_OPERATOR_METRICS,
    ):
        for expected_metric in endpoint_metrics:
            aggregator.assert_metric(expected_metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    for namespace in ("cluster_operator", "topic_operator", "user_operator"):
        aggregator.assert_service_check(
            f"strimzi.{namespace}.openmetrics.health",
            status=StrimziCheck.OK,
            count=1,
        )
    assert len(aggregator.service_check_names) == 3


@pytest.mark.parametrize(
    "instance",
    [
        {},
        {"openmetrics_endpoint": "http://cluster-operator:8080/metrics"},
    ],
)
def test_instance_without_operator_endpoint(dd_run_check, check, instance):
    with pytest.raises(
        Exception,
        match="Must specify at least one of the following:"
        "`cluster_operator_endpoint`, `topic_operator_endpoint` or `user_operator_endpoint`.",
    ):
        dd_run_check(check(instance))


@pytest.mark.parametrize(
    "namespace, instance, endpoint_key",
    [
        (
            "cluster_operator",
            MOCKED_CLUSTER_OPERATOR_INSTANCE,
            "cluster_operator_endpoint",
        ),
        (
            "topic_operator",
            MOCKED_TOPIC_OPERATOR_INSTANCE,
            "topic_operator_endpoint",
        ),
        (
            "user_operator",
            MOCKED_USER_OPERATOR_INSTANCE,
            "user_operator_endpoint",
        ),
    ],
)
def test_parse_config_populates_only_configured_scrapers(namespace, instance, endpoint_key, check):
    # Using a fixture simplifies the need to explicity define the class
    #   This is equivalent to StrimziCheck('strimzi', {}, [instance])
    strimzi = check(instance)
    strimzi.parse_config()
    assert len(strimzi.scraper_configs) == 1
    assert strimzi.scraper_configs[0][endpoint_key] == instance[endpoint_key]
    assert strimzi.scraper_configs[0]["openmetrics_endpoint"] == instance[endpoint_key]
    assert strimzi.scraper_configs[0]["namespace"] == "strimzi." + namespace
