# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import datetime as dt
import ssl

import pytest
from mock import ANY, MagicMock, patch
from pyVmomi import vim, vmodl

from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.api import APIConnectionError, VSphereAPI
from datadog_checks.vsphere.cache import InfrastructureCache
from datadog_checks.vsphere.config import VSphereConfig


@pytest.fixture(autouse=True)
def mock_vsan_stub():
    with patch('vsanapiutils.GetVsanVcStub') as GetStub:
        GetStub._stub.host = '0.0.0.0'
        yield GetStub


def test_ssl_verify_false(realtime_instance):
    realtime_instance['ssl_verify'] = False

    with patch('datadog_checks.vsphere.api.connect') as connect, patch(
        'ssl.SSLContext.load_verify_locations'
    ) as load_verify_locations:
        smart_connect = connect.SmartConnect

        config = VSphereConfig(realtime_instance, {}, MagicMock())
        VSphereAPI(config, MagicMock())

        actual_context = smart_connect.call_args.kwargs['sslContext']  # type: ssl.SSLContext
        assert actual_context.protocol == ssl.PROTOCOL_TLS
        assert actual_context.verify_mode == ssl.CERT_NONE
        load_verify_locations.assert_not_called()


def test_ssl_cert(realtime_instance):
    realtime_instance['ssl_verify'] = True
    realtime_instance['ssl_cafile'] = '/dummy/path/cafile.pem'
    realtime_instance['ssl_capath'] = '/dummy/path'

    with patch('datadog_checks.vsphere.api.connect') as connect, patch(
        'ssl.SSLContext.load_verify_locations'
    ) as load_verify_locations:
        smart_connect = connect.SmartConnect

        config = VSphereConfig(realtime_instance, {}, MagicMock())
        VSphereAPI(config, MagicMock())

        actual_context = smart_connect.call_args.kwargs['sslContext']  # type: ssl.SSLContext
        assert actual_context.protocol == ssl.PROTOCOL_TLS
        assert actual_context.verify_mode == ssl.CERT_REQUIRED
        assert actual_context.check_hostname is True
        load_verify_locations.assert_called_with(cafile=None, capath='/dummy/path')


def test_ssl_cafile(realtime_instance):
    realtime_instance['ssl_verify'] = True
    realtime_instance['ssl_capath'] = '/dummy/path'

    with patch('datadog_checks.vsphere.api.connect') as connect, patch(
        'ssl.SSLContext.load_verify_locations'
    ) as load_verify_locations:
        smart_connect = connect.SmartConnect

        config = VSphereConfig(realtime_instance, {}, MagicMock())
        VSphereAPI(config, MagicMock())

        actual_context = smart_connect.call_args.kwargs['sslContext']  # type: ssl.SSLContext
        assert actual_context.protocol == ssl.PROTOCOL_TLS
        assert actual_context.verify_mode == ssl.CERT_REQUIRED
        assert actual_context.check_hostname is True
        load_verify_locations.assert_called_with(cafile=None, capath='/dummy/path')


def test_ssl_capath(realtime_instance):
    realtime_instance['ssl_verify'] = True
    realtime_instance['ssl_cafile'] = '/dummy/path/cafile.pem'

    with patch('datadog_checks.vsphere.api.connect') as connect, patch(
        'ssl.SSLContext.load_verify_locations'
    ) as load_verify_locations:
        smart_connect = connect.SmartConnect

        config = VSphereConfig(realtime_instance, {}, MagicMock())
        VSphereAPI(config, MagicMock())

        actual_context = smart_connect.call_args.kwargs['sslContext']  # type: ssl.SSLContext
        assert actual_context.protocol == ssl.PROTOCOL_TLS
        assert actual_context.verify_mode == ssl.CERT_REQUIRED
        assert actual_context.check_hostname is True
        load_verify_locations.assert_called_with(cafile='/dummy/path/cafile.pem', capath=None)


def test_connect_success(realtime_instance):
    with patch('datadog_checks.vsphere.api.connect') as connect:
        connection = MagicMock()
        smart_connect = connect.SmartConnect
        smart_connect.return_value = connection
        get_about_info = connection.content.about.version.__str__

        config = VSphereConfig(realtime_instance, {}, MagicMock())
        api = VSphereAPI(config, MagicMock())
        smart_connect.assert_called_once_with(
            host=realtime_instance['host'],
            user=realtime_instance['username'],
            pwd=realtime_instance['password'],
            sslContext=ANY,
        )
        get_about_info.assert_called_once()

        assert api._conn == connection


def test_connect_failure(realtime_instance):
    with patch('datadog_checks.vsphere.api.connect') as connect:
        connection = MagicMock()
        smart_connect = connect.SmartConnect
        smart_connect.return_value = connection
        version_info = connection.content.about.version.__str__
        version_info.side_effect = Exception('foo')

        config = VSphereConfig(realtime_instance, {}, MagicMock())
        with pytest.raises(APIConnectionError):
            VSphereAPI(config, MagicMock())

        smart_connect.assert_called_once_with(
            host=realtime_instance['host'],
            user=realtime_instance['username'],
            pwd=realtime_instance['password'],
            sslContext=ANY,
        )
        version_info.assert_called_once()


def test_get_infrastructure(realtime_instance):
    with patch('datadog_checks.vsphere.api.connect'):
        config = VSphereConfig(realtime_instance, {}, MagicMock())
        api = VSphereAPI(config, MagicMock())

        container_view = api._conn.content.viewManager.CreateContainerView.return_value
        container_view.__class__ = vim.ManagedObject

        obj1 = MagicMock(missingSet=None, obj="foo")
        obj2 = MagicMock(missingSet=None, obj="bar")
        api._conn.content.propertyCollector.RetrievePropertiesEx.return_value = MagicMock(objects=[obj1], token=['baz'])
        api._conn.content.propertyCollector.ContinueRetrievePropertiesEx.return_value = MagicMock(
            objects=[obj2], token=None
        )

        root_folder = api._conn.content.rootFolder
        root_folder.name = 'root-folder'
        infrastructure_data = api.get_infrastructure()
        assert infrastructure_data == {'foo': {}, 'bar': {}, root_folder: {'name': 'root-folder', 'parent': None}}
        container_view.Destroy.assert_called_once()


@pytest.mark.parametrize(
    'exception, expected_calls',
    [
        (
            Exception('error'),
            2,
        ),
        (
            vmodl.fault.InvalidArgument(),
            1,
        ),
        (
            vim.fault.InvalidName(),
            1,
        ),
        (
            vim.fault.RestrictedByAdministrator(),
            1,
        ),
    ],
)
def test_smart_retry(realtime_instance, exception, expected_calls):
    with patch('datadog_checks.vsphere.api.connect') as connect:
        config = VSphereConfig(realtime_instance, {}, MagicMock())
        api = VSphereAPI(config, MagicMock())

        smart_connect = connect.SmartConnect
        disconnect = connect.Disconnect
        query_perf_counter = api._conn.content.perfManager.QueryPerfCounterByLevel
        query_perf_counter.side_effect = [exception, 'success']
        try:
            api.get_perf_counter_by_level(None)
        except Exception:
            pass
        assert query_perf_counter.call_count == expected_calls
        assert smart_connect.call_count == expected_calls
        assert disconnect.call_count == expected_calls - 1


def test_get_max_query_metrics(realtime_instance):
    with patch('datadog_checks.vsphere.api.connect'):
        config = VSphereConfig(realtime_instance, {}, MagicMock())
        api = VSphereAPI(config, MagicMock())
        values = [12, -1]
        expected = [12, float('inf')]

        for val, expect in zip(values, expected):
            query_config = MagicMock()
            query_config.return_value = [MagicMock(value=val)]
            api._conn.content.setting.QueryOptions = query_config
            max_metrics = api.get_max_query_metrics()
            assert max_metrics == expect
            query_config.assert_called_once_with("config.vpxd.stats.maxQueryMetrics")


def test_get_new_events_success_without_fallback(realtime_instance):
    with patch('datadog_checks.vsphere.api.connect'):
        config = VSphereConfig(realtime_instance, {}, MagicMock())
        api = VSphereAPI(config, MagicMock())

        returned_events = [vim.event.Event(), vim.event.Event(), vim.event.Event()]
        api._conn.content.eventManager.QueryEvents.return_value = returned_events

        events = api.get_new_events(start_time=dt.datetime.now())
        assert events == returned_events


def test_get_new_events_failure_without_fallback(realtime_instance):
    with patch('datadog_checks.vsphere.api.connect'):
        config = VSphereConfig(realtime_instance, {}, MagicMock())
        api = VSphereAPI(config, MagicMock())

        api._conn.content.eventManager.QueryEvents.side_effect = KeyError("some parse error")

        with pytest.raises(KeyError):
            api.get_new_events(start_time=dt.datetime.now())


def test_get_new_events_with_fallback(realtime_instance):
    realtime_instance['use_collect_events_fallback'] = True

    with patch('datadog_checks.vsphere.api.connect'):
        config = VSphereConfig(realtime_instance, {}, MagicMock())
        api = VSphereAPI(config, MagicMock())

        event1 = vim.event.Event(key=1)
        event3 = vim.event.Event(key=3)
        event_collector = MagicMock()
        api._conn.content.eventManager.QueryEvents.side_effect = [
            KeyError("some parse error"),
            [event1],
            KeyError("event parse error"),
            [event3],
        ]
        api._conn.content.eventManager.CreateCollectorForEvents.return_value = event_collector

        event_collector.ReadNextEvents.side_effect = [
            [event1],
            KeyError("event parse error"),
            [event3],
            [],
        ]

        events = api.get_new_events(start_time=dt.datetime.now())
        assert events == [event1, event3]


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api')
def test_vsan_metrics_api(aggregator, realtime_instance, dd_run_check):
    realtime_instance['collect_vsan_data'] = True

    with patch('datadog_checks.vsphere.api.connect'):
        with patch('pyVmomi.vim.cluster.VsanPerformanceManager') as MockVsanPerformanceManager:
            config = VSphereConfig(realtime_instance, {}, MagicMock())
            api = VSphereAPI(config, MagicMock())
            cluster = MagicMock(name='a', spec=vim.ClusterComputeResource)
            host = MagicMock(name='b')
            cluster.host = [host]
            cluster_nested_elts = {cluster: ['nested-id-1', 'nested-id-2']}
            entity_ref_ids = {
                'cluster': ['cluster-domclient:', 'vsan-cluster-capacity:'],
                'host': ['host-domclient:', 'host-cpu:'],
            }
            id_to_tags = {'nested-id-1': ['cluster'], 'nested-id-2': ['host']}
            starting_time = dt.datetime(2024, 1, 1)
            mock_vsan_events = api.get_vsan_events(starting_time)
            assert len(mock_vsan_events) == 0

            mock_vsan_perf_manager = MockVsanPerformanceManager.return_value
            mock_vsan_perf_manager.QueryClusterHealth.return_value = [
                MagicMock(
                    groupId='group-1',
                    groupHealth='green',
                    groupTests=[
                        MagicMock(testId='test.1', testHealth='green'),
                        MagicMock(testId='test.2', testHealth='yellow'),
                    ],
                )
            ]
            mock_vsan_perf_manager.QueryVsanPerf.return_value = [
                MagicMock(
                    entityRefId="cluster-domclient:nested-id-1",
                    value=[MagicMock(metricId=MagicMock(dynamicProperty=[]))],
                )
            ]

            health_metrics, performance_metrics = api.get_vsan_metrics(
                cluster_nested_elts, entity_ref_ids, id_to_tags, starting_time
            )

            assert len(health_metrics) == 1
            assert 'vsphere.vsan.cluster.health.count' in health_metrics[0]
            assert 'vsphere.vsan.cluster.health.1.count' in health_metrics[0]
            assert 'vsphere.vsan.cluster.health.2.count' in health_metrics[0]
            assert len(performance_metrics) == 1
            assert len(performance_metrics[0]) == 1

            vsan_config = MagicMock()
            vsan_config.enabled = True
            cluster.configurationEx.vsanConfigInfo = vsan_config
            cache = InfrastructureCache(float('inf'))
            cache.set_mor_props(cluster, {})
            cache.set_mor_props(host, {})
            check = VSphereCheck('vsphere', {}, [realtime_instance])
            check.infrastructure_cache = cache
            dd_run_check(check)

            aggregator.assert_metric('vsphere.vsan.cluster.health.count', value=1)
            aggregator.assert_metric('vsphere.vsan.cluster.health.1.count', count=0)
            aggregator.assert_metric('vsphere.vsan.cluster.health.2.count', count=0)


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api')
def test_vsan_empty_health_metrics(aggregator, realtime_instance, dd_run_check, caplog):
    realtime_instance['collect_vsan_data'] = True

    with patch('datadog_checks.vsphere.api.connect'):
        with patch('pyVmomi.vim.cluster.VsanPerformanceManager') as MockVsanPerformanceManager:
            config = VSphereConfig(realtime_instance, {}, MagicMock())
            api = VSphereAPI(config, MagicMock())
            cluster = MagicMock(name='a', spec=vim.ClusterComputeResource)
            host = MagicMock(name='b')
            cluster.host = [host]
            cluster_nested_elts = {cluster: ['nested-id-1', 'nested-id-2']}
            entity_ref_ids = {'type1': ['entity-1'], 'type2': ['entity-2']}
            id_to_tags = {'nested-id-1': ['type1'], 'nested-id-2': ['type2']}
            starting_time = dt.datetime(2024, 1, 1)
            mock_vsan_events = api.get_vsan_events(starting_time)
            assert len(mock_vsan_events) == 0

            mock_vsan_perf_manager = MockVsanPerformanceManager.return_value
            mock_vsan_perf_manager.QueryClusterHealth.return_value = []
            mock_vsan_perf_manager.QueryVsanPerf.return_value = [
                MagicMock(
                    entityRefId="cluster-domclient:nested-id-1",
                    value=[MagicMock(metricId=MagicMock(dynamicProperty=[]))],
                )
            ]

            health_metrics, performance_metrics = api.get_vsan_metrics(
                cluster_nested_elts, entity_ref_ids, id_to_tags, starting_time
            )
            assert len(health_metrics) == 0
