# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
from cm_client.models.api_cluster import ApiCluster
from cm_client.models.api_cluster_list import ApiClusterList
from cm_client.models.api_entity_tag import ApiEntityTag
from cm_client.models.api_version_info import ApiVersionInfo
from cm_client.rest import ApiException

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import CAN_CONNECT_TAGS, CLUSTER_HEALTH_TAGS, METRICS
from .conftest import get_timeseries_resource

pytestmark = [pytest.mark.unit]


def test_given_cloudera_check_when_get_version_exception_from_cloudera_client_then_emits_critical_service(
    dd_run_check,
    cloudera_check,
    instance,
    aggregator,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        side_effect=ApiException('Service not available'),
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


def test_given_cloudera_check_when_version_field_not_found_then_emits_critical_service(
    dd_run_check,
    cloudera_check,
    instance,
    aggregator,
):
    with mock.patch('cm_client.ClouderaManagerResourceApi.get_version', return_value=ApiVersionInfo(),), pytest.raises(
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
        message="Cloudera API Client is none: Cloudera Manager Version is unsupported or unknown: None",
        tags=CAN_CONNECT_TAGS,
    )


def test_given_cloudera_check_when_not_supported_version_then_emits_critical_service(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(version='5.0.0'),
    ), pytest.raises(
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
        message="Cloudera API Client is none: Cloudera Manager Version is unsupported or unknown: 5.0.0",
        tags=CAN_CONNECT_TAGS,
    )


def test_given_cloudera_check_when_v7_read_clusters_exception_from_cloudera_client_then_emits_critical_service(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(version="7.0.0"),
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        side_effect=ApiException('Service not available'),
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
    api_response,
    instance,
    list_hosts_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(version="7.0.0"),
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=ApiClusterList(
            items=[
                ApiCluster(
                    name="cod--qfdcinkqrzw",
                    entity_status="BAD_HEALTH",
                    tags=[
                        ApiEntityTag(name="_cldr_cb_clustertype", value="Data Hub"),
                        ApiEntityTag(name="_cldr_cb_origin", value="cloudbreak"),
                    ],
                    **api_response('cluster_good_health'),
                ),
            ],
        ),
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource(),
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
            tags=CLUSTER_HEALTH_TAGS,
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
    api_response,
    read_events_resource,
    instance,
    list_hosts_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(version="7.0.0"),
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=ApiClusterList(
            items=[
                ApiCluster(
                    name="cod--qfdcinkqrzw",
                    entity_status="GOOD_HEALTH",
                    tags=[
                        ApiEntityTag(name="_cldr_cb_clustertype", value="Data Hub"),
                        ApiEntityTag(name="_cldr_cb_origin", value="cloudbreak"),
                    ],
                    **api_response('cluster_good_health'),
                ),
            ],
        ),
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource(),
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
            tags=CLUSTER_HEALTH_TAGS,
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
    api_response,
    instance,
    list_hosts_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(version="7.0.0"),
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=ApiClusterList(
            items=[
                ApiCluster(
                    name="cod--qfdcinkqrzw",
                    entity_status="GOOD_HEALTH",
                    tags=[
                        ApiEntityTag(name="_cldr_cb_clustertype", value="Data Hub"),
                        ApiEntityTag(name="_cldr_cb_origin", value="cloudbreak"),
                    ],
                    **api_response('cluster_good_health'),
                ),
            ],
        ),
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource(),
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


def test_given_cloudera_check_when_autodiscover_configured_then_emits_configured_cluster_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    api_response,
    instance_autodiscover_include,
    list_hosts_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(version="7.0.0"),
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=ApiClusterList(
            items=[
                ApiCluster(
                    name="cod--qfdcinkqrzw",
                    entity_status="GOOD_HEALTH",
                    tags=[
                        ApiEntityTag(name="_cldr_cb_clustertype", value="Data Hub"),
                        ApiEntityTag(name="_cldr_cb_origin", value="cloudbreak"),
                    ],
                    **api_response('cluster_good_health'),
                ),
                ApiCluster(
                    name="tmp_cluster",
                    entity_status="GOOD_HEALTH",
                    tags=[
                        ApiEntityTag(name="_cldr_cb_clustertype", value="Data Hub"),
                        ApiEntityTag(name="_cldr_cb_origin", value="cloudbreak"),
                    ],
                    **api_response('cluster_good_health'),
                ),
            ],
        ),
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource(),
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=list_hosts_resource,
    ):
        # Given
        check = cloudera_check(instance_autodiscover_include)
        # When
        dd_run_check(check)
        # Then
        for category, metrics in METRICS.items():
            for metric in metrics:
                aggregator.assert_metric(f'cloudera.{category}.{metric}', count=1)
                aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_cluster")
        aggregator.assert_service_check('cloudera.can_connect', AgentCheck.OK, tags=CAN_CONNECT_TAGS)
        aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_HEALTH_TAGS, count=1)


def test_given_cloudera_check_when_autodiscover_exclude_configured_then_emits_configured_cluster_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    api_response,
    instance_autodiscover_exclude,
    list_hosts_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(version="7.0.0"),
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=ApiClusterList(
            items=[
                ApiCluster(
                    name="cod--qfdcinkqrzw",
                    entity_status="GOOD_HEALTH",
                    tags=[
                        ApiEntityTag(name="_cldr_cb_clustertype", value="Data Hub"),
                        ApiEntityTag(name="_cldr_cb_origin", value="cloudbreak"),
                    ],
                    **api_response('cluster_good_health'),
                ),
                ApiCluster(
                    name="tmp_cluster",
                    entity_status="GOOD_HEALTH",
                    tags=[
                        ApiEntityTag(name="_cldr_cb_clustertype", value="Data Hub"),
                        ApiEntityTag(name="_cldr_cb_origin", value="cloudbreak"),
                    ],
                    **api_response('cluster_good_health'),
                ),
            ],
        ),
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource(),
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=list_hosts_resource,
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
        aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_HEALTH_TAGS, count=1)


def test_given_cloudera_check_when_autodiscover_empty_clusters_then_emits_zero_cluster_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    api_response,
    instance_autodiscover_include,
    list_hosts_resource,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(version="7.0.0"),
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=ApiClusterList(
            items=[],
        ),
    ), mock.patch(
        'cm_client.TimeSeriesResourceApi.query_time_series',
        side_effect=get_timeseries_resource(),
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=list_hosts_resource,
    ):
        # Given
        check = cloudera_check(instance_autodiscover_include)
        # When
        dd_run_check(check)
        # Then
        for category, metrics in METRICS.items():
            for metric in metrics:
                aggregator.assert_metric(f'cloudera.{category}.{metric}', count=0)

        aggregator.assert_service_check('cloudera.can_connect', AgentCheck.OK, tags=CAN_CONNECT_TAGS)
        aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_HEALTH_TAGS, count=0)
