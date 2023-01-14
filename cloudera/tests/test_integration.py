# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.cloudera import ClouderaCheck
from datadog_checks.cloudera.metrics import TIMESERIES_METRICS

from .common import CAN_CONNECT_TAGS, CLUSTER_1_HEALTH_TAGS, METRICS


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_given_bad_url_when_check_runs_then_service_check_critical(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance_bad_url,
):
    with pytest.raises(Exception, match="HTTPConnectionPool"):
        # Given
        check = cloudera_check(instance_bad_url)
        # When
        dd_run_check(check)
    # Then
    aggregator.assert_service_check('cloudera.can_connect', ClouderaCheck.CRITICAL)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_given_api_v48_endpoint_when_check_runs_then_service_check_ok_and_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
):
    # Given
    check = cloudera_check(instance)
    # When
    dd_run_check(check)
    # Then
    for category, metrics in METRICS.items():
        for metric in metrics:
            aggregator.assert_metric(f'cloudera.{category}.{metric}', at_least=1)
            aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_cluster")
            aggregator.assert_metric_has_tag(f'cloudera.{category}.{metric}', "test1")

            # Only non-cluster metrics have rack_id tags
            if category != 'cluster':
                aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_rack_id")

            # Host metrics should not have a cloudera_host tag, since cloudera_hostname already exists
            if category == "host":
                aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_host:", count=0)
                aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_hostname")

    # All timeseries metrics should have cloudera_{category} tag
    for category, metrics in TIMESERIES_METRICS.items():
        for metric in metrics:
            aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', f"cloudera_{category}")

    aggregator.assert_service_check(
        'cloudera.can_connect',
        ClouderaCheck.OK,
        tags=CAN_CONNECT_TAGS,
    )
    aggregator.assert_service_check(
        'cloudera.cluster.health',
        ClouderaCheck.OK,
        tags=CLUSTER_1_HEALTH_TAGS,
    )
    aggregator.assert_service_check('cloudera.host.health', ClouderaCheck.OK)
    aggregator.assert_event(
        "ExecutionException running extraction tasks for service 'cod--qfdcinkqrzw::yarn'.", count=1
    )
    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_metadata(cloudera_check, instance, datadog_agent, dd_run_check):
    check = cloudera_check(instance)
    check.check_id = 'test:123'
    dd_run_check(check)

    raw_version = '7.2.15'
    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'cloudera',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
