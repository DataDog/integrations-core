# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import datetime as dt
import os

import pytest
from mock import MagicMock, Mock, patch
from pyVmomi import vim, vmodl

from datadog_checks.vsphere.legacy.vsphere_legacy import DEFAULT_MAX_HIST_METRICS

from .common import LAB_INSTANCE, PERF_COUNTER_INFO, PERF_ENTITY_METRICS, PERF_METRIC_ID, PROPERTIES_EX, VSPHERE_VERSION
from .mocked_api import MockedAPI, mock_http_rest_api_v6, mock_http_rest_api_v7

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


@pytest.fixture(scope='session')
def dd_environment():
    yield LAB_INSTANCE


@pytest.fixture()
def instance():
    return {
        'empty_default_hostname': True,
        'use_legacy_check_version': False,
        'host': 'vsphere_host',
        'username': 'vsphere_username',
        'password': 'vsphere_password',
    }


@pytest.fixture()
def realtime_instance():
    return {
        'collection_level': 4,
        'empty_default_hostname': True,
        'use_legacy_check_version': False,
        'host': os.environ.get('VSPHERE_URL', 'FAKE'),
        'username': os.environ.get('VSPHERE_USERNAME', 'FAKE'),
        'password': os.environ.get('VSPHERE_PASSWORD', 'FAKE'),
        'ssl_verify': False,
        'rest_api_options': None,
    }


@pytest.fixture()
def historical_instance():
    return {
        'collection_level': 1,
        'empty_default_hostname': True,
        'use_legacy_check_version': False,
        'host': os.environ.get('VSPHERE_URL', 'FAKE'),
        'username': os.environ.get('VSPHERE_USERNAME', 'FAKE'),
        'password': os.environ.get('VSPHERE_PASSWORD', 'FAKE'),
        'ssl_verify': False,
        'collection_type': 'historical',
    }


@pytest.fixture()
def events_only_instance():
    return {
        'empty_default_hostname': True,
        'use_legacy_check_version': False,
        'host': os.environ.get('VSPHERE_URL', 'FAKE'),
        'username': os.environ.get('VSPHERE_USERNAME', 'FAKE'),
        'password': os.environ.get('VSPHERE_PASSWORD', 'FAKE'),
        'ssl_verify': False,
        'collect_events_only': True,
    }


@pytest.fixture
def mock_type():
    """
    mock the result of the `type` built-in function to work on mock.MagicMock().
    Without the fixture, type(MagicMock(spec=int)) = MagicMock
    With the fixture, type(MagicMock(spec=int)) = int
    """
    paths = [
        'datadog_checks.vsphere.cache.type',
        'datadog_checks.vsphere.utils.type',
        'datadog_checks.vsphere.vsphere.type',
        'datadog_checks.vsphere.api_rest.type',
    ]
    with ExitStack() as stack:
        new_type_function = lambda x: x.__class__ if isinstance(x, Mock) else type(x)  # noqa: E731
        for path in paths:
            type_function = stack.enter_context(patch(path))
            type_function.side_effect = new_type_function
        yield


@pytest.fixture
def mock_threadpool():
    with patch('datadog_checks.vsphere.vsphere.ThreadPoolExecutor') as pool, patch(
        'datadog_checks.vsphere.vsphere.as_completed', side_effect=lambda x: x
    ):
        pool.return_value.submit = lambda f, args: MagicMock(
            done=MagicMock(return_value=True), result=MagicMock(return_value=f(args)), exception=lambda: None
        )
        yield


@pytest.fixture
def mock_api():
    with patch('datadog_checks.vsphere.vsphere.VSphereAPI', MockedAPI):
        yield


@pytest.fixture
def query_events():
    def QueryEvents(filter):
        return []

    yield QueryEvents


@pytest.fixture
def query_options():
    def QueryOptions(name):
        return [MagicMock(value=DEFAULT_MAX_HIST_METRICS)]

    yield QueryOptions


@pytest.fixture
def query_available_perf_metric():
    def QueryAvailablePerfMetric(entity, begin_time=None, end_time=None, interval_id=None):
        return PERF_METRIC_ID

    yield QueryAvailablePerfMetric


@pytest.fixture
def query_perf_counter_by_level():
    def QueryPerfCounterByLevel(collection_level):
        return PERF_COUNTER_INFO

    yield QueryPerfCounterByLevel


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


@pytest.fixture
def mock_connect(
    query_events,
    query_options,
    query_available_perf_metric,
    query_perf_counter_by_level,
    query_perf,
    retrieve_properties_ex,
):
    with patch('pyVim.connect.SmartConnect') as mock_connect, patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = MagicMock()
        mock_si.content.about.version = VSPHERE_VERSION
        mock_si.content.about.build = '123456789'
        mock_si.content.about.apiType = 'VirtualCenter'
        mock_si.CurrentTime.return_value = dt.datetime.now()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents = query_events
        mock_si.content.setting.QueryOptions = query_options
        mock_si.content.perfManager.QueryAvailablePerfMetric = query_available_perf_metric
        mock_si.content.perfManager.QueryPerfCounterByLevel = query_perf_counter_by_level
        mock_si.content.perfManager.QueryPerf = query_perf
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx = retrieve_properties_ex
        mock_connect.return_value = mock_si
        yield


@pytest.fixture
def mock_rest_api():
    if VSPHERE_VERSION.startswith('7.'):
        with patch('requests.api.request', mock_http_rest_api_v7):
            yield
    else:
        with patch('requests.api.request', mock_http_rest_api_v6):
            yield
