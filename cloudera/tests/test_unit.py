# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import CAN_CONNECT_TAGS, CLUSTER_1_HEALTH_TAGS, CLUSTER_TMP_HEALTH_TAGS, METRICS
from .conftest import get_timeseries_resource

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize('cloudera_api_exception', ['Service not available'], indirect=True)
def test_given_cloudera_check_when_get_version_exception_from_cloudera_client_then_emits_critical_service(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_api_exception,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        side_effect=cloudera_api_exception,
    ), pytest.raises(
        Exception,
        match='Service not available',
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
    # Then
    aggregator.assert_service_check(
        'cloudera.can_connect',
        AgentCheck.CRITICAL,
        tags=CAN_CONNECT_TAGS,
    )


@pytest.mark.parametrize('cloudera_version', [None, '5.0.0'], indirect=True)
def test_given_cloudera_check_when_version_unsupported_or_unknown_then_emits_critical_service(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
):
    with mock.patch('cm_client.ClouderaManagerResourceApi.get_version', return_value=cloudera_version,), pytest.raises(
        Exception,
        match='Cloudera Manager Version is unsupported or unknown',
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
    # Then
    aggregator.assert_service_check(
        'cloudera.can_connect',
        AgentCheck.CRITICAL,
        message="Cloudera API Client is none: Cloudera Manager Version is unsupported or unknown:"
        f" {cloudera_version.version}",
        tags=CAN_CONNECT_TAGS,
    )


@pytest.mark.parametrize('cloudera_api_exception', ['Service not available'], indirect=True)
def test_given_cloudera_check_when_v7_read_clusters_exception_from_cloudera_client_then_emits_critical_service(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version_7_0_0,
    cloudera_api_exception,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        side_effect=cloudera_api_exception,
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
    aggregator.assert_service_check(
        'cloudera.can_connect',
        AgentCheck.CRITICAL,
        tags=CAN_CONNECT_TAGS,
        message="Cloudera check raised an exception: (Service not available)\nReason: None\n",
    )


def test_given_cloudera_check_when_bad_health_cluster_then_emits_cluster_health_critical(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version_7_0_0,
    list_one_cluster_bad_health_resource,
    list_hosts_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=list_one_cluster_bad_health_resource,
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource,
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=list_hosts_resource,
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
        aggregator.assert_service_check(
            'cloudera.cluster.health',
            AgentCheck.CRITICAL,
            message='BAD_HEALTH',
            tags=CLUSTER_1_HEALTH_TAGS,
        )
        aggregator.assert_service_check(
            'cloudera.can_connect',
            AgentCheck.OK,
            tags=CAN_CONNECT_TAGS,
        )


def test_given_cloudera_check_when_good_health_cluster_then_emits_cluster_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version_7_0_0,
    list_one_cluster_good_health_resource,
    list_hosts_resource,
    read_events_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=list_one_cluster_good_health_resource,
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource,
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=list_hosts_resource,
    ), mock.patch(
        'cm_client.EventsResourceApi.read_events',
        return_value=read_events_resource,
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
        for category, metrics in METRICS.items():
            for metric in metrics:
                aggregator.assert_metric(f'cloudera.{category}.{metric}')

        aggregator.assert_service_check(
            'cloudera.can_connect',
            AgentCheck.OK,
            tags=CAN_CONNECT_TAGS,
        )
        aggregator.assert_service_check(
            'cloudera.cluster.health',
            AgentCheck.OK,
            tags=CLUSTER_1_HEALTH_TAGS,
        )
        expected_msg_text = (
            'Interceptor for {http://yarn.extractor.cdx.cloudera.com/}YarnHistoryClient '
            'has thrown exception, unwinding now'
        )

        aggregator.assert_event(msg_text=expected_msg_text, count=1)
        aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
        aggregator.assert_all_metrics_covered()


def test_given_cloudera_check_when_no_events_response_then_no_event_collection(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version_7_0_0,
    list_one_cluster_good_health_resource,
    list_hosts_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=list_one_cluster_good_health_resource,
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource,
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=list_hosts_resource,
    ), mock.patch(
        'cm_client.EventsResourceApi.read_events',
        side_effect=Exception,
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
        aggregator.assert_service_check(
            'cloudera.can_connect',
            AgentCheck.OK,
            tags=CAN_CONNECT_TAGS,
        )
        expected_content = (
            'Interceptor for {http://yarn.extractor.cdx.cloudera.com/}YarnHistoryClient '
            'has thrown exception, unwinding now'
        )
        # verify that event is not collected, but check still works normally
        aggregator.assert_event(msg_text=expected_content, count=0)


def test_autodiscover_clusters_configured_include_not_array_then_exception_is_raised(
    dd_run_check,
    cloudera_check,
    instance_autodiscover_clusters_include_not_array,
    cloudera_version_7_0_0,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), pytest.raises(
        Exception,
        match='Setting `include` must be an array',
    ):
        check = cloudera_check(instance_autodiscover_clusters_include_not_array)
        dd_run_check(check)


def test_given_cloudera_check_when_autodiscover_configured_with_one_entry_dict_then_emits_configured_cluster_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance_autodiscover_include_with_one_entry_dict,
    cloudera_version_7_0_0,
    list_two_clusters_with_one_tmp_resource,
    list_hosts_resource,
    read_events_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=list_two_clusters_with_one_tmp_resource,
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource,
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=list_hosts_resource,
    ), mock.patch(
        'cm_client.EventsResourceApi.read_events',
        return_value=read_events_resource,
    ):
        # Given
        check = cloudera_check(instance_autodiscover_include_with_one_entry_dict)
        # When
        dd_run_check(check)
        # Then
        for category, metrics in METRICS.items():
            for metric in metrics:
                aggregator.assert_metric(f'cloudera.{category}.{metric}', count=1)
                aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_cluster")
        aggregator.assert_service_check('cloudera.can_connect', AgentCheck.OK, tags=CAN_CONNECT_TAGS)
        aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_1_HEALTH_TAGS, count=1)


def test_given_cloudera_check_when_autodiscover_configured_with_two_entries_dict_then_emits_configured_cluster_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance_autodiscover_include_with_two_entries_dict,
    cloudera_version_7_0_0,
    list_two_clusters_with_one_tmp_resource,
    list_hosts_resource,
    read_events_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=list_two_clusters_with_one_tmp_resource,
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource,
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=list_hosts_resource,
    ), mock.patch(
        'cm_client.EventsResourceApi.read_events',
        return_value=read_events_resource,
    ):
        # Given
        check = cloudera_check(instance_autodiscover_include_with_two_entries_dict)
        # When
        dd_run_check(check)
        # Then
        for category, metrics in METRICS.items():
            for metric in metrics:
                aggregator.assert_metric(f'cloudera.{category}.{metric}', count=2)
                aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_cluster")
        aggregator.assert_service_check('cloudera.can_connect', AgentCheck.OK, tags=CAN_CONNECT_TAGS)
        aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_1_HEALTH_TAGS, count=1)
        aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_TMP_HEALTH_TAGS, count=1)


def test_given_cloudera_check_when_autodiscover_configured_with_str_then_emits_configured_cluster_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance_autodiscover_include_with_str,
    cloudera_version_7_0_0,
    list_two_clusters_with_one_tmp_resource,
    list_hosts_resource,
    read_events_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=list_two_clusters_with_one_tmp_resource,
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource,
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=list_hosts_resource,
    ), mock.patch(
        'cm_client.EventsResourceApi.read_events',
        return_value=read_events_resource,
    ):
        # Given
        check = cloudera_check(instance_autodiscover_include_with_str)
        # When
        dd_run_check(check)
        # Then
        for category, metrics in METRICS.items():
            for metric in metrics:
                aggregator.assert_metric(f'cloudera.{category}.{metric}', count=1)
                aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_cluster")
        aggregator.assert_service_check('cloudera.can_connect', AgentCheck.OK, tags=CAN_CONNECT_TAGS)
        aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_1_HEALTH_TAGS, count=1)


def test_given_cloudera_check_when_autodiscover_exclude_configured_then_emits_configured_cluster_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance_autodiscover_exclude,
    cloudera_version_7_0_0,
    list_two_clusters_with_one_tmp_resource,
    list_hosts_resource,
    read_events_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=list_two_clusters_with_one_tmp_resource,
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource,
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=list_hosts_resource,
    ), mock.patch(
        'cm_client.EventsResourceApi.read_events',
        return_value=read_events_resource,
    ):
        # Given
        check = cloudera_check(instance_autodiscover_exclude)
        # When
        dd_run_check(check)
        # Then
        for category, metrics in METRICS.items():
            for metric in metrics:
                aggregator.assert_metric(f'cloudera.{category}.{metric}', count=1)
                aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_cluster")
        aggregator.assert_service_check('cloudera.can_connect', AgentCheck.OK, tags=CAN_CONNECT_TAGS)
        aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_1_HEALTH_TAGS, count=1)


def test_given_cloudera_check_when_autodiscover_empty_clusters_then_emits_zero_cluster_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance_autodiscover_include_with_one_entry_dict,
    cloudera_version_7_0_0,
    list_empty_clusters_resource,
    list_hosts_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=list_empty_clusters_resource,
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource,
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=list_hosts_resource,
    ):
        # Given
        check = cloudera_check(instance_autodiscover_include_with_one_entry_dict)
        # When
        dd_run_check(check)
        # Then
        for category, metrics in METRICS.items():
            for metric in metrics:
                aggregator.assert_metric(f'cloudera.{category}.{metric}', count=0)

        aggregator.assert_service_check('cloudera.can_connect', AgentCheck.OK, tags=CAN_CONNECT_TAGS)
        aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_1_HEALTH_TAGS, count=0)
