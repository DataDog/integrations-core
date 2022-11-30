# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
import six
from cm_client.models.api_cluster import ApiCluster
from cm_client.models.api_cluster_list import ApiClusterList
from cm_client.models.api_entity_tag import ApiEntityTag
from cm_client.models.api_host import ApiHost
from cm_client.models.api_host_list import ApiHostList
from cm_client.models.api_time_series import ApiTimeSeries
from cm_client.models.api_time_series_data import ApiTimeSeriesData
from cm_client.models.api_time_series_metadata import ApiTimeSeriesMetadata
from cm_client.models.api_time_series_response import ApiTimeSeriesResponse
from cm_client.models.api_time_series_response_list import ApiTimeSeriesResponseList
from cm_client.models.api_version_info import ApiVersionInfo
from cm_client.rest import ApiException

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.cloudera.metrics import METRICS
from six import PY2


# from datadog_checks.cloudera.queries import TIMESERIES_QUERIES

pytestmark = [pytest.mark.unit]


def test_given_cloudera_check_when_py2_then_raises_exception(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
):
    with mock.patch.object(six, 'PY2'), pytest.raises(
        ConfigurationError, match='This version of the integration is only available when using py3'
    ):
        # Given
        cloudera_check(instance)


def test_given_cloudera_check_when_get_version_exception_from_cloudera_client_then_emits_critical_service(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        side_effect=ApiException('Service not available'),
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
        aggregator.assert_service_check('cloudera.can_connect', AgentCheck.CRITICAL)


def test_given_cloudera_check_when_version_field_not_found_then_emits_critical_service(
    aggregator,
    dd_run_check,
    cloudera_check,
    api_response,
    instance,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(),
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
        aggregator.assert_service_check('cloudera.can_connect', AgentCheck.CRITICAL)


def test_given_cloudera_check_when_not_supported_version_then_emits_critical_service(
    aggregator,
    dd_run_check,
    cloudera_check,
    api_response,
    instance,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(version='5.0.0'),
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
        aggregator.assert_service_check('cloudera.can_connect', AgentCheck.CRITICAL)


def test_given_cloudera_check_when_supported_version_then_emits_ok_service(
    aggregator,
    dd_run_check,
    cloudera_check,
    api_response,
    instance,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(version="7.0.0"),
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=ApiClusterList(
            items=[
                ApiCluster(
                    name="cluster_1",
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
        side_effect=[
            ApiTimeSeriesResponseList(
                items=[
                    ApiTimeSeriesResponse(
                        time_series=[
                            ApiTimeSeries(
                                data=[
                                    ApiTimeSeriesData(value=49.7),
                                ],
                                metadata=ApiTimeSeriesMetadata(metric_name=metric, entity_name=category),
                            )
                            for metric in metrics
                        ]
                    ),
                ],
            )
            for category, metrics in METRICS.items()
        ],
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=ApiHostList(
            items=[ApiHost(host_id='host_1')],
        ),
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
        aggregator.assert_service_check('cloudera.can_connect', AgentCheck.OK)


# def test_given_cloudera_check_when_v5_read_clusters_exception_from_cloudera_client_then_emits_critical_service(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     api_response,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=ApiVersionInfo(version="5.0.0"),
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.read_clusters',
#         side_effect=ApiException('Service not available'),
#     ):
#         # Given
#         instance = {}
#         check = cloudera_check(instance)
#         # When
#         dd_run_check(check)
#         # Then
#         aggregator.assert_service_check('cloudera.can_connect', AgentCheck.CRITICAL)


def test_given_cloudera_check_when_v7_read_clusters_exception_from_cloudera_client_then_emits_critical_service(
    aggregator,
    dd_run_check,
    cloudera_check,
    api_response,
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
        aggregator.assert_service_check('cloudera.can_connect', AgentCheck.CRITICAL)


def test_given_cloudera_check_when_bad_health_cluster_then_emits_cluster_health_critical(
    aggregator,
    dd_run_check,
    cloudera_check,
    api_response,
    instance,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(version="7.0.0"),
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=ApiClusterList(
            items=[
                ApiCluster(
                    name="cluster_1",
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
        side_effect=[
            ApiTimeSeriesResponseList(
                items=[
                    ApiTimeSeriesResponse(
                        time_series=[
                            ApiTimeSeries(
                                data=[
                                    ApiTimeSeriesData(value=49.7),
                                ],
                                metadata=ApiTimeSeriesMetadata(metric_name=metric, entity_name=category),
                            )
                            for metric in metrics
                        ]
                    ),
                ],
            )
            for category, metrics in METRICS.items()
        ],
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=ApiHostList(
            items=[ApiHost(host_id='host_1')],
        ),
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
        aggregator.assert_service_check(
            'cloudera.cluster.health',
            AgentCheck.CRITICAL,
            tags=['_cldr_cb_clustertype:Data Hub', '_cldr_cb_origin:cloudbreak', 'cloudera_cluster:cluster_1'],
        )


def test_given_cloudera_check_when_good_health_cluster_then_emits_cluster_health_ok(
    aggregator,
    dd_run_check,
    cloudera_check,
    api_response,
    instance,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(version="7.0.0"),
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=ApiClusterList(
            items=[
                ApiCluster(
                    name="cluster_1",
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
        side_effect=[
            ApiTimeSeriesResponseList(
                items=[
                    ApiTimeSeriesResponse(
                        time_series=[
                            ApiTimeSeries(
                                data=[
                                    ApiTimeSeriesData(value=49.7),
                                ],
                                metadata=ApiTimeSeriesMetadata(metric_name=metric, entity_name=category),
                            )
                            for metric in metrics
                        ]
                    ),
                ],
            )
            for category, metrics in METRICS.items()
        ],
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=ApiHostList(
            items=[ApiHost(host_id='host_1')],
        ),
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
        aggregator.assert_service_check(
            'cloudera.cluster.health',
            AgentCheck.OK,
            tags=['_cldr_cb_clustertype:Data Hub', '_cldr_cb_origin:cloudbreak', 'cloudera_cluster:cluster_1'],
        )


def test_given_cloudera_check_when_good_health_cluster_then_emits_cluster_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    api_response,
    instance,
):
    with mock.patch(
        'cm_client.ClouderaManagerResourceApi.get_version',
        return_value=ApiVersionInfo(version="7.0.0"),
    ), mock.patch(
        'cm_client.ClustersResourceApi.read_clusters',
        return_value=ApiClusterList(
            items=[
                ApiCluster(
                    name="cluster_1",
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
        side_effect=[
            ApiTimeSeriesResponseList(
                items=[
                    ApiTimeSeriesResponse(
                        time_series=[
                            ApiTimeSeries(
                                data=[
                                    ApiTimeSeriesData(value=49.7),
                                ],
                                metadata=ApiTimeSeriesMetadata(metric_name=metric, entity_name=category),
                            )
                            for metric in metrics
                        ]
                    ),
                ],
            )
            for category, metrics in METRICS.items()
        ],
    ), mock.patch(
        'cm_client.ClustersResourceApi.list_hosts',
        return_value=ApiHostList(
            items=[ApiHost(host_id='host_1')],
        ),
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
        for category, metrics in METRICS.items():
            for metric in metrics:
                aggregator.assert_metric(f'cloudera.{category}.{metric}')


# def test_run_timeseries_checks(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
# ):
#     # Given
#     instance = {
#         'run_timeseries': True,
#         'username': 'csso_shri.subramanian',
#         'password': 'wyz*xbw7cej*mbh9VUW',
#         'api_url': 'https://cod--qfdcinkqrzw-gateway.agent-in.jfha-h5rc.a0.cloudera.site/'
#         'cod--qfdcinkqrzw/cdp-proxy-api/cm-api/v48',
#     }
#     check = cloudera_check(instance)
#     # When
#     dd_run_check(check)
#     # Then
#     for metric in TIMESERIES_QUERIES:
#         metric_name = metric['metric_name']
#         for category in metric['categories']:
#             aggregator.assert_metric(f'cloudera.{category}.{metric_name}')