# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import datetime as dt

import pytest
from mock import MagicMock, Mock, patch
from pyVmomi import vim

from datadog_checks.vsphere.constants import DEFAULT_MAX_QUERY_METRICS

from .common import (
    DEFAULT_INSTANCE,
    EVENTS,
    EVENTS_ONLY_INSTANCE,
    HISTORICAL_INSTANCE,
    LAB_INSTANCE,
    LEGACY_DEFAULT_INSTANCE,
    LEGACY_HISTORICAL_INSTANCE,
    LEGACY_REALTIME_INSTANCE,
    PERF_COUNTER_INFO,
    PERF_ENTITY_METRICS,
    PERF_METRIC_ID,
    PROPERTIES_EX,
    REALTIME_INSTANCE,
    VM_INVALID_GATEWAY_PROPERTIES_EX,
    VM_INVALID_PROPERTIES_EX,
    VM_PROPERTIES_EX,
    VSPHERE_VERSION,
    MockHttpV6,
    MockHttpV7,
)
from .mocked_api import MockedAPI, mock_http_rest_api_v6, mock_http_rest_api_v7

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


@pytest.fixture(scope='session')
def dd_environment():
    yield LAB_INSTANCE.copy()


@pytest.fixture()
def legacy_default_instance():
    return LEGACY_DEFAULT_INSTANCE.copy()


@pytest.fixture()
def legacy_realtime_instance():
    return LEGACY_REALTIME_INSTANCE.copy()


@pytest.fixture()
def legacy_historical_instance():
    return LEGACY_HISTORICAL_INSTANCE.copy()


@pytest.fixture()
def default_instance():
    return DEFAULT_INSTANCE.copy()


@pytest.fixture()
def realtime_instance():
    return REALTIME_INSTANCE.copy()


@pytest.fixture()
def historical_instance():
    return HISTORICAL_INSTANCE.copy()


@pytest.fixture()
def events_only_instance():
    return EVENTS_ONLY_INSTANCE.copy()


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
    with patch('datadog_checks.vsphere.vsphere.VSphereAPI') as mocked_api:
        mocked_api.side_effect = MockedAPI
        yield mocked_api


@pytest.fixture
def query_events():
    def QueryEvents(filter):
        return EVENTS

    yield QueryEvents


@pytest.fixture
def query_options():
    def QueryOptions(name):
        return [MagicMock(value=DEFAULT_MAX_QUERY_METRICS)]

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
def properties_ex():
    return PROPERTIES_EX


@pytest.fixture
def vm_properties_ex():
    return VM_PROPERTIES_EX


@pytest.fixture
def vm_invalid_properties_ex():
    return VM_INVALID_PROPERTIES_EX


@pytest.fixture
def vm_invalid_gateway_properties_ex():
    return VM_INVALID_GATEWAY_PROPERTIES_EX


@pytest.fixture
def retrieve_properties_ex(properties_ex):
    def RetrievePropertiesEx(spec_set, options):
        return properties_ex

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
def connect_exception():
    mock_si = MagicMock()
    mock_si.side_effect = Exception("Connection error")
    with patch('pyVim.connect.SmartConnect', side_effect=mock_si):
        yield mock_si


@pytest.fixture
def get_timestamp():
    with patch('datadog_checks.vsphere.vsphere.get_timestamp') as mock_time:
        yield mock_time


@pytest.fixture(scope="function", autouse=True)
def service_instance(
    query_events,
    query_options,
    query_available_perf_metric,
    query_perf_counter_by_level,
    query_perf,
    retrieve_properties_ex,
):
    mock_si = MagicMock()
    mock_si.content.about.version = VSPHERE_VERSION
    mock_si.content.about.build = '123456789'
    mock_si.content.about.apiType = 'VirtualCenter'
    mock_si.CurrentTime.return_value = dt.datetime.now()
    mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
    mock_si.content.eventManager.QueryEvents = MagicMock(side_effect=query_events)
    mock_si.content.setting.QueryOptions = MagicMock(side_effect=query_options)
    mock_si.content.perfManager.QueryAvailablePerfMetric = MagicMock(side_effect=query_available_perf_metric)
    mock_si.content.perfManager.QueryPerfCounterByLevel = MagicMock(side_effect=query_perf_counter_by_level)
    mock_si.content.perfManager.QueryPerf = MagicMock(side_effect=query_perf)
    mock_si.content.propertyCollector.RetrievePropertiesEx = MagicMock(side_effect=retrieve_properties_ex)
    with patch('pyVmomi.vmodl.query.PropertyCollector.ObjectSpec', return_value=MagicMock()), patch(
        'pyVmomi.vmodl.query.PropertyCollector.FilterSpec', return_value=MagicMock()
    ), patch('pyVim.connect.SmartConnect', return_value=mock_si):
        yield mock_si


@pytest.fixture
def mock_http_api(monkeypatch):
    if VSPHERE_VERSION.startswith('7.'):
        http = MockHttpV7()
    else:
        http = MockHttpV6()
    monkeypatch.setattr('requests.get', MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', MagicMock(side_effect=http.post))
    yield http


@pytest.fixture
def mock_rest_api():
    if VSPHERE_VERSION.startswith('7.'):
        with patch('requests.api.request', mock_http_rest_api_v7):
            yield
    else:
        with patch('requests.api.request', mock_http_rest_api_v6):
            yield
