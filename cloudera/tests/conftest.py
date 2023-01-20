# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from copy import deepcopy

import pytest
from cm_client.models.api_cluster import ApiCluster
from cm_client.models.api_cluster_list import ApiClusterList
from cm_client.models.api_cluster_ref import ApiClusterRef
from cm_client.models.api_entity_tag import ApiEntityTag
from cm_client.models.api_event import ApiEvent
from cm_client.models.api_event_attribute import ApiEventAttribute
from cm_client.models.api_event_query_result import ApiEventQueryResult
from cm_client.models.api_host import ApiHost
from cm_client.models.api_host_list import ApiHostList
from cm_client.models.api_time_series import ApiTimeSeries
from cm_client.models.api_time_series_data import ApiTimeSeriesData
from cm_client.models.api_time_series_metadata import ApiTimeSeriesMetadata
from cm_client.models.api_time_series_response import ApiTimeSeriesResponse
from cm_client.models.api_time_series_response_list import ApiTimeSeriesResponseList
from cm_client.models.api_version_info import ApiVersionInfo
from cm_client.rest import ApiException

from datadog_checks.cloudera import ClouderaCheck
from datadog_checks.cloudera.metrics import TIMESERIES_METRICS
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = common.COMPOSE_FILE
    conditions = [
        CheckDockerLogs(identifier='cloudera', patterns=['server running']),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [common.INSTANCE],
            'init_config': common.INIT_CONFIG,
        }


@pytest.fixture
def config():
    return {
        'instances': [common.INSTANCE],
        'init_config': common.INIT_CONFIG,
    }


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE)


@pytest.fixture
def instance_bad_url():
    return deepcopy(common.INSTANCE_BAD_URL)


@pytest.fixture
def instance_autodiscover_include_not_array():
    return deepcopy(common.INSTANCE_AUTODISCOVER_INCLUDE_NOT_ARRAY)


@pytest.fixture
def instance_autodiscover_include_with_one_entry_dict():
    return deepcopy(common.INSTANCE_AUTODISCOVER_INCLUDE_WITH_ONE_ENTRY_DICT)


@pytest.fixture
def instance_autodiscover_include_with_two_entries_dict():
    return deepcopy(common.INSTANCE_AUTODISCOVER_INCLUDE_WITH_TWO_ENTRIES_DICT)


@pytest.fixture
def instance_autodiscover_include_with_str():
    return deepcopy(common.INSTANCE_AUTODISCOVER_INCLUDE_WITH_STR)


@pytest.fixture
def instance_autodiscover_exclude():
    return deepcopy(common.INSTANCE_AUTODISCOVER_EXCLUDE)


@pytest.fixture
def init_config():
    return deepcopy(common.INIT_CONFIG)


@pytest.fixture(scope='session')
def cloudera_check():
    return lambda instance: deepcopy(ClouderaCheck('cloudera', init_config=common.INIT_CONFIG, instances=[instance]))


def get_timeseries_resource(query):
    return ApiTimeSeriesResponseList(
        items=[
            ApiTimeSeriesResponse(
                time_series=[
                    ApiTimeSeries(
                        data=[
                            ApiTimeSeriesData(value=49.7),
                        ],
                        metadata=ApiTimeSeriesMetadata(attributes={'category': category}, alias=metric),
                    )
                    for metric in metrics
                ]
            )
            for category, metrics in TIMESERIES_METRICS.items()
            if re.search(f'category={category.upper()}', query)
        ]
    )


@pytest.fixture
def cloudera_api_exception(request):
    return ApiException(request.param)


@pytest.fixture
def cloudera_version(request):
    return ApiVersionInfo() if request.param is None else ApiVersionInfo(version=request.param)


@pytest.fixture
def cloudera_version_7_0_0():
    return ApiVersionInfo(version='7.0.0')


@pytest.fixture
def list_empty_clusters_resource():
    return ApiClusterList(
        items=[],
    )


@pytest.fixture
def list_one_cluster_bad_health_resource():
    return ApiClusterList(
        items=[
            ApiCluster(
                name="cluster_1",
                entity_status="BAD_HEALTH",
                tags=[
                    ApiEntityTag(name="_cldr_cb_clustertype", value="Data Hub"),
                    ApiEntityTag(name="_cldr_cb_origin", value="cloudbreak"),
                ],
                cluster_type="COMPUTE_CLUSTER",
            ),
        ],
    )


@pytest.fixture
def list_one_cluster_good_health_resource():
    return ApiClusterList(
        items=[
            ApiCluster(
                name="cluster_1",
                entity_status="GOOD_HEALTH",
                tags=[
                    ApiEntityTag(name="_cldr_cb_clustertype", value="Data Hub"),
                    ApiEntityTag(name="_cldr_cb_origin", value="cloudbreak"),
                ],
                cluster_type="COMPUTE_CLUSTER",
            ),
        ],
    )


@pytest.fixture
def list_two_clusters_with_one_tmp_resource():
    return ApiClusterList(
        items=[
            ApiCluster(
                name="cluster_1",
                entity_status="GOOD_HEALTH",
                tags=[
                    ApiEntityTag(name="_cldr_cb_clustertype", value="Data Hub"),
                    ApiEntityTag(name="_cldr_cb_origin", value="cloudbreak"),
                ],
                cluster_type="COMPUTE_CLUSTER",
            ),
            ApiCluster(
                name="tmp_cluster",
                entity_status="GOOD_HEALTH",
                tags=[
                    ApiEntityTag(name="_cldr_cb_clustertype", value="Data Hub"),
                    ApiEntityTag(name="_cldr_cb_origin", value="cloudbreak"),
                ],
                cluster_type="COMPUTE_CLUSTER",
            ),
        ],
    )


@pytest.fixture
def list_hosts_resource():
    return ApiHostList(
        items=[
            ApiHost(
                host_id='host_1',
                cluster_ref=ApiClusterRef(
                    cluster_name="cluster_1",
                    display_name="cluster_1",
                ),
                num_cores=8,
                num_physical_cores=4,
                total_phys_mem_bytes=33079799808,
            )
        ],
    )


@pytest.fixture
def read_events_resource():
    content = (
        'Interceptor for {http://yarn.extractor.cdx.cloudera.com/}YarnHistoryClient has thrown exception, unwinding now'
    )
    dummy_event = ApiEvent(
        time_occurred='2022-11-30T21:06:39.870Z',
        severity='IMPORTANT',
        content=content,
        category='LOG_EVENT',
        attributes=[
            ApiEventAttribute(name='ROLE', values=['TELEMETRYPUBLISHER']),
            ApiEventAttribute(name='CLUSTER', values=['cod--qfdcinkqrzw']),
            ApiEventAttribute(name='ROLE_DISPLAY_NAME', values=['Telemetry Publisher (cod--qfdcinkqrzw-gateway0)']),
        ],
    )
    return ApiEventQueryResult(items=[dummy_event])
