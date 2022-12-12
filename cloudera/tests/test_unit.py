# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
import six
from cm_client.models.api_cluster import ApiCluster
from cm_client.models.api_cluster_list import ApiClusterList
from cm_client.models.api_cluster_ref import ApiClusterRef
from cm_client.models.api_entity_tag import ApiEntityTag
from cm_client.models.api_host import ApiHost
from cm_client.models.api_host_list import ApiHostList
from cm_client.models.api_version_info import ApiVersionInfo
from cm_client.rest import ApiException

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.cloudera.metrics import METRICS
from datadog_checks.dev.utils import get_metadata_metrics

from .common import CAN_CONNECT_TAGS, CLUSTER_HEALTH_TAGS
from .conftest import get_timeseries_resource

pytestmark = [pytest.mark.unit]


def test_given_cloudera_check_when_py2_then_raises_exception(
    cloudera_check,
    instance,
):
    with mock.patch.object(six, 'PY2'), pytest.raises(
        ConfigurationError,
        match='This version of the integration is only available when using py3',
    ):
        cloudera_check(instance)


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
        return_value=ApiHostList(
            items=[
                ApiHost(
                    host_id='host_1',
                    cluster_ref=ApiClusterRef(
                        cluster_name="cod--qfdcinkqrzw",
                        display_name="cod--qfdcinkqrzw",
                    ),
                )
            ],
        ),
    ):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
        aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
        aggregator.assert_service_check(
            'cloudera.can_connect',
            AgentCheck.OK,
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
        return_value=ApiHostList(
            items=[
                ApiHost(
                    host_id='host_1',
                    cluster_ref=ApiClusterRef(
                        cluster_name="cod--qfdcinkqrzw",
                        display_name="cod--qfdcinkqrzw",
                    ),
                )
            ],
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
            tags=CLUSTER_HEALTH_TAGS,
        )
        aggregator.assert_service_check(
            'cloudera.can_connect',
            AgentCheck.OK,
            tags=CAN_CONNECT_TAGS,
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
        return_value=ApiHostList(
            items=[
                ApiHost(
                    host_id='host_1',
                    cluster_ref=ApiClusterRef(
                        cluster_name="cod--qfdcinkqrzw",
                        display_name="cod--qfdcinkqrzw",
                    ),
                )
            ],
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
        return_value=ApiHostList(
            items=[
                ApiHost(
                    host_id='host_1',
                    cluster_ref=ApiClusterRef(
                        cluster_name="cod--qfdcinkqrzw",
                        display_name="cod--qfdcinkqrzw",
                    ),
                    num_cores=8,
                    num_physical_cores=4,
                    total_phys_mem_bytes=33079799808,
                )
            ],
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
