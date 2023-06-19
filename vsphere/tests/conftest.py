# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import datetime as dt
import os

import pytest
from mock import MagicMock, Mock, patch
from pyVmomi import vim, vmodl

from .common import LAB_INSTANCE, VSPHERE_VERSION
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
def mock_connect():
    with patch('pyVim.connect.SmartConnect') as mock_connect, patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = MagicMock()
        mock_si.content.about.version = VSPHERE_VERSION
        mock_si.content.about.build = '123456789'
        mock_si.content.about.apiType = 'VirtualCenter'
        mock_si.CurrentTime.return_value = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryAvailablePerfMetric.return_value = [
            vim.PerformanceManager.MetricId(counterId=100),
        ]
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='datastore'),
                nameInfo=vim.ElementDescription(key='busResets'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
                unitInfo=vim.ElementDescription(key='command'),
            ),
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.Datastore(moId="NFS-Share-1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[2, 5],
                        id=vim.PerformanceManager.MetricId(
                            counterId=100,
                            instance='ds1',
                        ),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.Datastore(moId="NFS-Share-1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='NFS-Share-1',
                        ),
                    ],
                ),
            ],
        )
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
