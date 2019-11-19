import pytest
from mock import ANY, MagicMock, patch
from pyVmomi import vim

from datadog_checks.vsphere.api import APIConnectionError, VSphereAPI


def test_connect_success(realtime_instance):
    with patch('datadog_checks.vsphere.api.connect') as connect:
        connection = MagicMock()
        smart_connect = connect.SmartConnect
        smart_connect.return_value = connection
        current_time = connection.CurrentTime

        api = VSphereAPI(realtime_instance)
        smart_connect.assert_called_once_with(
            host=realtime_instance['host'],
            user=realtime_instance['username'],
            pwd=realtime_instance['password'],
            sslContext=ANY,
        )
        current_time.assert_called_once()

        assert api._conn == connection


def test_connect_failure(realtime_instance):
    with patch('datadog_checks.vsphere.api.connect') as connect:
        connection = MagicMock()
        smart_connect = connect.SmartConnect
        smart_connect.return_value = connection
        current_time = connection.CurrentTime
        current_time.side_effect = Exception('foo')

        with pytest.raises(APIConnectionError):
            VSphereAPI(realtime_instance)

        smart_connect.assert_called_once_with(
            host=realtime_instance['host'],
            user=realtime_instance['username'],
            pwd=realtime_instance['password'],
            sslContext=ANY,
        )
        current_time.assert_called_once()


def test_get_infrastructure(realtime_instance):
    with patch('datadog_checks.vsphere.api.connect'):
        api = VSphereAPI(realtime_instance)

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


def test_smart_retry(realtime_instance):
    with patch('datadog_checks.vsphere.api.connect') as connect:
        smart_connect = connect.SmartConnect
        api = VSphereAPI(realtime_instance)
        query_perf_counter = api._conn.content.perfManager.QueryPerfCounterByLevel
        query_perf_counter.side_effect = [Exception('error'), 'success']
        api.get_perf_counter_by_level(None)

        assert query_perf_counter.call_count == 2
        assert smart_connect.call_count == 2


def test_get_max_query_metrics(realtime_instance):
    with patch('datadog_checks.vsphere.api.connect'):
        api = VSphereAPI(realtime_instance)
        values = [12, -1]
        expected = [12, float('inf')]

        for val, expect in zip(values, expected):
            query_config = MagicMock()
            query_config.return_value = [MagicMock(value=val)]
            api._conn.content.setting.QueryOptions = query_config
            max_metrics = api.get_max_query_metrics()
            assert max_metrics == expect
            query_config.assert_called_once_with("config.vpxd.stats.maxQueryMetrics")
