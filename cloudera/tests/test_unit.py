# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import CAN_CONNECT_TAGS, CLUSTER_1_HEALTH_TAGS, METRICS
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


def test_given_custom_queries_then_retrieve_metrics_unit(
    aggregator,
    dd_run_check,
    cloudera_check,
    list_one_cluster_good_health_resource,
    cloudera_version_7_0_0,
    instance,
    get_custom_timeseries_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=list_one_cluster_good_health_resource,
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        return_value=get_custom_timeseries_resource,
    ):
        # Given
        instance['custom_queries'] = [
            {'query': "select foo"},  # foo is given category of cluster in common.py
        ]

        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
        aggregator.assert_metric("cloudera.cluster.foo")


@pytest.mark.parametrize(
    'instance_autodiscover',
    [
        {'clusters': {'include': {'^cluster.*'}}},
    ],
    ids=["clusters configured not a list"],
    indirect=['instance_autodiscover'],
)
def test_autodiscover_clusters_configured_include_not_array_then_exception_is_raised(
    dd_run_check,
    cloudera_check,
    instance_autodiscover,
    cloudera_version_7_0_0,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), pytest.raises(
        Exception,
        match='Setting `include` must be an array',
    ):
        check = cloudera_check(instance_autodiscover)
        dd_run_check(check)


@pytest.mark.parametrize(
    'instance_autodiscover, read_clusters, list_hosts, dd_run_check_count, expected_list',
    [
        (
            {'clusters': {}},
            {'number': 0, 'prefix': [], 'status': ['GOOD_HEALTH']},
            {'number': 0, 'prefix': []},
            1,
            [{'metric_count': 0, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': ['.*']}},
            {'number': 0, 'prefix': [], 'status': ['GOOD_HEALTH']},
            {'number': 0, 'prefix': []},
            1,
            [{'metric_count': 0, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': ['.*']}},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0, 'prefix': []},
            1,
            [{'metric_count': 1, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': ['.*']}},
            {'number': 10, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0, 'prefixes': []},
            1,
            [{'metric_count': 10, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': ['^cluster_.*']}},
            {'number': 1, 'prefix': ['cluster_', 'tmp_'], 'status': ['GOOD_HEALTH']},
            {'number': 0, 'prefixes': []},
            1,
            [{'metric_count': 1, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': ['.*'], 'exclude': ['^tmp_*']}},
            {'number': 1, 'prefix': ['cluster_', 'tmp_'], 'status': ['GOOD_HEALTH']},
            {'number': 0, 'prefixes': []},
            1,
            [{'metric_count': 1, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': ['.*'], 'limit': 5}},
            {'number': 10, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0, 'prefixes': []},
            1,
            [{'metric_count': 5, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': ['.*']}},
            {'number': 10, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0, 'prefixes': []},
            2,
            [{'metric_count': 20, 'call_count': 2}],
        ),
        (
            {'clusters': {'include': ['.*'], 'interval': 60}},
            {'number': 10, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0, 'prefixes': []},
            2,
            [{'metric_count': 20, 'call_count': 1}],
        ),
    ],
    ids=[
        "empty clusters",
        "include all clusters / read 0 clusters",
        "include all clusters / read 1 cluster",
        "include all clusters / read 10 clusters",
        "include 'cluster_*' clusters / read 2 clusters ('cluster_0' and 'tmp_0')",
        "include all and exclude 'tmp_*' clusters / read 2 clusters ('cluster_0' and 'tmp_0')",
        "include all and limit to 5 / read 10 clusters",
        "include all in two runs / read 10 clusters",
        "include all and interval to 60 in two runs / read 10 clusters",
    ],
    indirect=[
        'instance_autodiscover',
        'read_clusters',
        'list_hosts',
    ],
)
def test_autodiscover_clusters(
    instance_autodiscover,
    read_clusters,
    list_hosts,
    dd_run_check_count,
    expected_list,
    cloudera_version_7_0_0,
    cloudera_check,
    dd_run_check,
    aggregator,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=read_clusters,
    ) as mocked_read_clusters, mock.patch(
        'cm_client.EventsResourceApi.read_events',
        side_effect=Exception,
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource,
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=list_hosts,
    ):
        check = cloudera_check(instance_autodiscover)
        for _ in range(dd_run_check_count):
            dd_run_check(check)
        for expected in expected_list:
            for metric in METRICS['cluster']:
                aggregator.assert_metric(f'cloudera.cluster.{metric}', count=expected['metric_count'])
            assert mocked_read_clusters.call_count == expected['call_count']


@pytest.mark.parametrize(
    'instance_autodiscover, read_clusters',
    [
        (
            {'tags': ['test1'], 'clusters': {'include': [{'.*': {'hosts': {'include': {'^host.*'}}}}]}},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
        ),
    ],
    ids=["hosts configured not a list"],
    indirect=[
        'instance_autodiscover',
        'read_clusters',
    ],
)
def test_autodiscover_hosts_configured_include_not_array_then_emits_critical_service(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance_autodiscover,
    read_clusters,
    cloudera_version_7_0_0,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), mock.patch('cm_client.ClustersResourceApi.read_clusters', return_value=read_clusters,), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource,
    ):
        check = cloudera_check(instance_autodiscover)
        dd_run_check(check)
        aggregator.assert_service_check(
            'cloudera.can_connect',
            AgentCheck.CRITICAL,
            message='Cloudera check raised an exception: Setting `include` must be an array',
            tags=CAN_CONNECT_TAGS,
        )


@pytest.mark.parametrize(
    'instance_autodiscover, read_clusters, list_hosts, dd_run_check_count, expected_list',
    [
        (
            {'clusters': {}},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0, 'prefix': []},
            1,
            [{'metric_count': 0, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': [{'.*': {'hosts': {'include': ['.*']}}}]}},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0, 'prefix': []},
            1,
            [{'metric_count': 0, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': [{'.*': {'hosts': {'include': ['.*']}}}]}},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_']},
            1,
            [{'metric_count': 1, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': [{'.*': {'hosts': {'include': ['.*']}}}]}},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 5, 'prefix': ['host_']},
            1,
            [{'metric_count': 5, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': [{'.*': {'hosts': {'include': ['.*']}}}]}},
            {'number': 2, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_']},
            1,
            [{'metric_count': 2, 'call_count': 2}],
        ),
        (
            {'clusters': {'include': [{'.*': {'hosts': {'include': ['^host_.*']}}}]}},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_', 'tmp_']},
            1,
            [{'metric_count': 1, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': [{'.*': {'hosts': {'include': ['.*'], 'exclude': ['^tmp_.*']}}}]}},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_', 'tmp_']},
            1,
            [{'metric_count': 1, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': [{'.*': {'hosts': {'include': ['.*'], 'limit': 5}}}]}},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 10, 'prefix': ['host_']},
            1,
            [{'metric_count': 5, 'call_count': 1}],
        ),
        (
            {'clusters': {'include': [{'.*': {'hosts': {'include': ['.*']}}}]}},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 10, 'prefix': ['host_']},
            2,
            [{'metric_count': 20, 'call_count': 2}],
        ),
        (
            {'clusters': {'include': [{'.*': {'hosts': {'include': ['.*'], 'interval': 60}}}]}},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 10, 'prefix': ['host_']},
            2,
            [{'metric_count': 20, 'call_count': 1}],
        ),
    ],
    ids=[
        "empty hosts",
        "include all hosts / read 1 cluster with 0 hosts",
        "include all hosts/ read 1 cluster with 1 host",
        "include all hosts/ read 1 cluster with 5 hosts",
        "include all hosts/ read 2 clusters with 1 host each",
        "include 'host_*' hosts / read 1 cluster with 2 hosts ('host_0' and 'tmp_0')",
        "include all and exclude 'tmp_*' hosts / read 1 cluster with 2 hosts ('host_0' and 'tmp_0')",
        "include all and limit to 5 / read 1 cluster with 10 hosts",
        "include all in two runs / read 1 cluster with 10 hosts",
        "include all and interval to 60 in two runs / read 1 cluster with 10 hosts",
    ],
    indirect=[
        'instance_autodiscover',
        'read_clusters',
        'list_hosts',
    ],
)
def test_autodiscover_hosts(
    instance_autodiscover,
    read_clusters,
    list_hosts,
    dd_run_check_count,
    expected_list,
    cloudera_version_7_0_0,
    cloudera_check,
    dd_run_check,
    aggregator,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=cloudera_version_7_0_0,
    ), mock.patch('cm_client.ClustersResourceApi.read_clusters', return_value=read_clusters,), mock.patch(
        'cm_client.EventsResourceApi.read_events',
        side_effect=Exception,
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource,
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=list_hosts,
    ) as mocked_list_hosts:
        check = cloudera_check(instance_autodiscover)
        for _ in range(dd_run_check_count):
            dd_run_check(check)
        for expected in expected_list:
            for metric in METRICS['host']:
                aggregator.assert_metric(f'cloudera.host.{metric}', count=expected['metric_count'])
            assert mocked_list_hosts.call_count == expected['call_count']
