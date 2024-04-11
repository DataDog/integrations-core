# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from mock import MagicMock, patch
from pyVmomi import vim

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitForPortListening
from datadog_checks.dev.fs import get_here

from .common import (
    BASE_INSTANCE,
    HOST,
    PERF_COUNTER_INFO,
    PERF_ENTITY_METRICS,
    PERF_METRIC_ID,
    PORT,
    PROPERTIES_EX,
    VCSIM_INSTANCE,
)


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), 'docker', 'docker-compose.yaml')
    conditions = [
        WaitForPortListening(HOST, PORT, wait=10),
        CheckDockerLogs(compose_file, 'export GOVC_URL', wait=10),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield VCSIM_INSTANCE


@pytest.fixture
def instance():
    return BASE_INSTANCE


@pytest.fixture
def vcsim_instance():
    return VCSIM_INSTANCE


@pytest.fixture
def query_available_perf_metric():
    def QueryAvailablePerfMetric(entity, begin_time=None, end_time=None, interval_id=None):
        return PERF_METRIC_ID

    yield QueryAvailablePerfMetric


@pytest.fixture
def retrieve_properties_ex():
    def RetrievePropertiesEx(spec_set, options):
        return PROPERTIES_EX

    yield RetrievePropertiesEx


@pytest.fixture
def query_perf():
    def QueryPerf(query_specs):
        result = []
        for query_spec in query_specs:
            for entity_metric in PERF_ENTITY_METRICS:
                if query_spec.entity == entity_metric.entity:
                    value = []
                    for metric_id in query_spec.metricId:
                        for metric_value in entity_metric.value:
                            if metric_id.counterId == metric_value.id.counterId:
                                value.append(metric_value)
                    result.append(
                        vim.PerformanceManager.EntityMetric(
                            entity=entity_metric.entity,
                            value=value,
                        )
                    )
        return result

    yield QueryPerf


@pytest.fixture(scope="function")
def service_instance(
    query_available_perf_metric,
    query_perf,
    retrieve_properties_ex,
):
    mock_si = MagicMock()
    mock_si.content.about.version = '6.5.0'
    mock_si.content.about.build = '123456789'
    mock_si.content.about.apiType = 'HostAgent'
    mock_si.content.about.fullName = 'VMware ESXi 6.5.0 build-123456789'
    mock_si.content.perfManager.perfCounter = PERF_COUNTER_INFO
    mock_si.content.perfManager.QueryAvailablePerfMetric = MagicMock(side_effect=query_available_perf_metric)
    mock_si.content.perfManager.QueryPerf = MagicMock(side_effect=query_perf)
    mock_si.content.propertyCollector.RetrievePropertiesEx = MagicMock(side_effect=retrieve_properties_ex)

    with patch('pyVmomi.vmodl.query.PropertyCollector.ObjectSpec', return_value=MagicMock()), patch(
        'pyVmomi.vmodl.query.PropertyCollector.FilterSpec', return_value=MagicMock()
    ), patch('pyVim.connect.SmartConnect', return_value=mock_si):
        yield mock_si
