# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import datetime as dt
import ssl

import pytest
from mock import ANY, MagicMock, PropertyMock, patch
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

    with (
        patch('datadog_checks.vsphere.api.connect') as connect,
        patch('ssl.SSLContext.load_verify_locations') as load_verify_locations,
    ):
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

    with (
        patch('datadog_checks.vsphere.api.connect') as connect,
        patch('ssl.SSLContext.load_verify_locations') as load_verify_locations,
    ):
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

    with (
        patch('datadog_checks.vsphere.api.connect') as connect,
        patch('ssl.SSLContext.load_verify_locations') as load_verify_locations,
    ):
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

    with (
        patch('datadog_checks.vsphere.api.connect') as connect,
        patch('ssl.SSLContext.load_verify_locations') as load_verify_locations,
    ):
        smart_connect = connect.SmartConnect

        config = VSphereConfig(realtime_instance, {}, MagicMock())
        VSphereAPI(config, MagicMock())

        actual_context = smart_connect.call_args.kwargs['sslContext']  # type: ssl.SSLContext
        assert actual_context.protocol == ssl.PROTOCOL_TLS
        assert actual_context.verify_mode == ssl.CERT_REQUIRED
        assert actual_context.check_hostname is True
        load_verify_locations.assert_called_with(cafile='/dummy/path/cafile.pem', capath=None)


def test_ssl_ciphers_with_ssl_verify_false(realtime_instance):
    realtime_instance['ssl_verify'] = False
    realtime_instance['ssl_ciphers'] = ['AES256-SHA', 'AES128-SHA']

    with (
        patch('datadog_checks.vsphere.api.connect') as connect,
        patch('ssl.SSLContext.set_ciphers') as set_ciphers,
    ):
        smart_connect = connect.SmartConnect

        config = VSphereConfig(realtime_instance, {}, MagicMock())
        VSphereAPI(config, MagicMock())

        actual_context = smart_connect.call_args.kwargs['sslContext']  # type: ssl.SSLContext
        assert actual_context.verify_mode == ssl.CERT_NONE
        set_ciphers.assert_called_once_with('AES256-SHA:AES128-SHA')


def test_ssl_ciphers_with_ssl_capath(realtime_instance):
    realtime_instance['ssl_verify'] = True
    realtime_instance['ssl_capath'] = '/dummy/path'
    realtime_instance['ssl_ciphers'] = ['AES256-SHA', 'AES128-SHA']

    with (
        patch('datadog_checks.vsphere.api.connect') as connect,
        patch('ssl.SSLContext.load_verify_locations') as load_verify_locations,
        patch('ssl.SSLContext.set_ciphers') as set_ciphers,
    ):
        smart_connect = connect.SmartConnect

        config = VSphereConfig(realtime_instance, {}, MagicMock())
        VSphereAPI(config, MagicMock())

        actual_context = smart_connect.call_args.kwargs['sslContext']  # type: ssl.SSLContext
        assert actual_context.verify_mode == ssl.CERT_REQUIRED
        assert actual_context.check_hostname is True
        load_verify_locations.assert_called_with(cafile=None, capath='/dummy/path')
        set_ciphers.assert_called_once_with('AES256-SHA:AES128-SHA')


def test_ssl_ciphers_with_ssl_verify_default(realtime_instance):
    realtime_instance['ssl_verify'] = True
    realtime_instance['ssl_ciphers'] = ['AES256-SHA', 'AES128-SHA']

    with (
        patch('datadog_checks.vsphere.api.connect') as connect,
        patch('ssl.SSLContext.set_ciphers') as set_ciphers,
    ):
        smart_connect = connect.SmartConnect

        config = VSphereConfig(realtime_instance, {}, MagicMock())
        VSphereAPI(config, MagicMock())

        actual_context = smart_connect.call_args.kwargs['sslContext']  # type: ssl.SSLContext
        assert actual_context.verify_mode == ssl.CERT_REQUIRED
        assert actual_context.check_hostname is True
        set_ciphers.assert_called_once_with('AES256-SHA:AES128-SHA')


def test_no_ssl_ciphers_default_behavior(realtime_instance):
    realtime_instance['ssl_verify'] = True

    with patch('datadog_checks.vsphere.api.connect') as connect:
        smart_connect = connect.SmartConnect

        config = VSphereConfig(realtime_instance, {}, MagicMock())
        VSphereAPI(config, MagicMock())

        actual_context = smart_connect.call_args.kwargs['sslContext']
        assert actual_context is None


_MISSING = object()


@pytest.mark.parametrize(
    'ssl_ciphers_value',
    [
        pytest.param(_MISSING, id='key_missing'),
        pytest.param(None, id='explicit_none'),
        pytest.param([], id='empty_list'),
    ],
)
def test_no_ssl_ciphers_with_context_created(realtime_instance, ssl_ciphers_value):
    realtime_instance['ssl_verify'] = False
    if ssl_ciphers_value is not _MISSING:
        realtime_instance['ssl_ciphers'] = ssl_ciphers_value

    with (
        patch('datadog_checks.vsphere.api.connect'),
        patch('ssl.SSLContext.set_ciphers') as set_ciphers,
    ):
        config = VSphereConfig(realtime_instance, {}, MagicMock())
        VSphereAPI(config, MagicMock())

        set_ciphers.assert_not_called()


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


def make_health_result():
    return [
        MagicMock(
            groupId='group-1',
            groupHealth='green',
            groupTests=[MagicMock(testId='test.1', testHealth='green')],
        )
    ]


def make_perf_result():
    return [
        MagicMock(
            entityRefId="cluster-domclient:nested-id-1",
            value=[MagicMock(metricId=MagicMock(dynamicProperty=[]))],
        )
    ]


def logged_warnings(log):
    return [call.args[0] % call.args[1:] for call in log.warning.call_args_list]


@pytest.fixture
def vsan_api(realtime_instance):
    """A VSphereAPI with a mocked vSAN performance manager and a real-enough logger to assert on."""
    realtime_instance['collect_vsan_data'] = True
    with (
        patch('datadog_checks.vsphere.api.connect'),
        patch('pyVmomi.vim.cluster.VsanPerformanceManager') as MockVsanPerformanceManager,
    ):
        config = VSphereConfig(realtime_instance, {}, MagicMock())
        log = MagicMock()
        yield VSphereAPI(config, log), MockVsanPerformanceManager.return_value, log


ENTITY_REF_IDS = {
    'cluster': ['cluster-domclient:', 'vsan-cluster-capacity:'],
    'host': ['host-domclient:', 'host-cpu:'],
}
ID_TO_TAGS = {'nested-id-1': ['cluster'], 'nested-id-2': ['host']}


@pytest.mark.parametrize(
    'failing_call',
    ['QueryClusterHealth', 'QueryVsanPerf'],
)
def test_vsan_metrics_failure_on_one_cluster_keeps_the_others(vsan_api, failing_call):
    """A single unhealthy cluster must not wipe out vSAN collection for the whole vCenter."""
    api, perf_manager, log = vsan_api
    bad_cluster = MagicMock(spec=vim.ClusterComputeResource)
    bad_cluster.name = 'IADC01'
    good_cluster = MagicMock(spec=vim.ClusterComputeResource)
    good_cluster.name = 'NHDC01'
    error = vim.fault.NotFound(msg='Stats primary cannot be found in the cluster.')

    def only_bad_cluster_fails(*args):
        if bad_cluster in args:
            raise error
        return make_health_result() if failing_call == 'QueryClusterHealth' else make_perf_result()

    getattr(perf_manager, failing_call).side_effect = only_bad_cluster_fails
    other_call = 'QueryVsanPerf' if failing_call == 'QueryClusterHealth' else 'QueryClusterHealth'
    getattr(perf_manager, other_call).return_value = (
        make_perf_result() if other_call == 'QueryVsanPerf' else make_health_result()
    )

    health_metrics, performance_metrics = api.get_vsan_metrics(
        {bad_cluster: ['nested-id-1'], good_cluster: ['nested-id-1']},
        ENTITY_REF_IDS,
        ID_TO_TAGS,
        dt.datetime(2024, 1, 1),
    )

    assert len(health_metrics) == 1
    assert health_metrics[0]['vsphere.vsan.cluster.health.count']['vsphere_cluster'] == 'NHDC01'
    assert len(performance_metrics) == 1
    warnings = logged_warnings(log)
    assert len(warnings) == 1
    assert 'IADC01' in warnings[0]
    assert 'Stats primary cannot be found in the cluster.' in warnings[0]


def test_vsan_metrics_unexpected_health_payload_skips_only_that_cluster(vsan_api):
    """vCenter 9.x can return a health group without `groupId`; that must not drop the other clusters."""
    api, perf_manager, log = vsan_api
    bad_cluster = MagicMock(spec=vim.ClusterComputeResource)
    bad_cluster.name = 'MADC06'
    good_cluster = MagicMock(spec=vim.ClusterComputeResource)
    good_cluster.name = 'NHDC01'

    def health_without_group_id(*args):
        if bad_cluster in args:
            return [MagicMock(spec=[])]
        return make_health_result()

    perf_manager.QueryClusterHealth.side_effect = health_without_group_id
    perf_manager.QueryVsanPerf.return_value = make_perf_result()

    health_metrics, _ = api.get_vsan_metrics(
        {bad_cluster: ['nested-id-1'], good_cluster: ['nested-id-1']},
        ENTITY_REF_IDS,
        ID_TO_TAGS,
        dt.datetime(2024, 1, 1),
    )

    assert len(health_metrics) == 1
    assert health_metrics[0]['vsphere.vsan.cluster.health.count']['vsphere_cluster'] == 'NHDC01'
    warnings = logged_warnings(log)
    assert len(warnings) == 1
    assert 'MADC06' in warnings[0]
    assert 'groupId' in warnings[0]


def test_vsan_metrics_reports_cluster_by_id_when_its_name_is_unreachable(vsan_api):
    """Looking up `name` hits vCenter, so it can fail too. Fall back to the managed object id."""
    api, perf_manager, log = vsan_api
    bad_cluster = MagicMock()
    bad_cluster._moId = 'domain-c3489'
    type(bad_cluster).name = PropertyMock(side_effect=vim.fault.NotAuthenticated(msg='Session is not authenticated.'))
    perf_manager.QueryClusterHealth.return_value = make_health_result()
    perf_manager.QueryVsanPerf.return_value = make_perf_result()

    health_metrics, _ = api.get_vsan_metrics(
        {bad_cluster: ['nested-id-1']},
        ENTITY_REF_IDS,
        ID_TO_TAGS,
        dt.datetime(2024, 1, 1),
    )

    assert len(health_metrics) == 0
    warnings = logged_warnings(log)
    assert len(warnings) == 1
    assert 'domain-c3489' in warnings[0]


def test_vsan_metrics_reports_every_failed_cluster_in_a_single_warning(vsan_api):
    """A dead session fails every cluster; that must stay one warning per run, not one per cluster."""
    api, perf_manager, log = vsan_api
    clusters = {}
    for cluster_name in ('NHDC01', 'PRDC01', 'MADC01'):
        cluster = MagicMock(spec=vim.ClusterComputeResource)
        cluster.name = cluster_name
        clusters[cluster] = ['nested-id-1']
    perf_manager.QueryClusterHealth.side_effect = vim.fault.NotAuthenticated(msg='Session is not authenticated.')

    health_metrics, _ = api.get_vsan_metrics(clusters, ENTITY_REF_IDS, ID_TO_TAGS, dt.datetime(2024, 1, 1))

    assert len(health_metrics) == 0
    warnings = logged_warnings(log)
    assert len(warnings) == 1
    for cluster_name in ('NHDC01', 'PRDC01', 'MADC01'):
        assert cluster_name in warnings[0]
    assert 'Session is not authenticated.' in warnings[0]
