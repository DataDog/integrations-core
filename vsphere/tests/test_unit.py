import pytest
from datadog_checks.base import AgentCheck
import mock

from datadog_checks.vsphere import VSphereCheck

from .common import VSPHERE_VERSION

pytestmark = [pytest.mark.unit]


def test_service_check_critical(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock(side_effect=Exception("Connection error"))
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        with pytest.raises(Exception):
            check = VSphereCheck('vsphere', {}, [events_only_instance])
            dd_run_check(check)
        aggregator.assert_service_check("vsphere.can_connect", AgentCheck.CRITICAL, tags=['vcenter_server:FAKE'])


def test_service_check_ok(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        check = VSphereCheck('vsphere', {}, [events_only_instance])
        dd_run_check(check)
        aggregator.assert_service_check("vsphere.can_connect", AgentCheck.OK, tags=['vcenter_server:FAKE'])


def test_metadata(datadog_agent, aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        mock_si = mock.MagicMock()
        mock_si.content.about.version = VSPHERE_VERSION
        mock_si.content.about.build = '123456789'
        mock_si.content.about.apiType = 'VirtualCenter'
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [events_only_instance])
        check.check_id = 'test:123'
        dd_run_check(check)
        major, minor, patch = VSPHERE_VERSION.split('.')
        version_metadata = {
            'version.scheme': 'semver',
            'version.major': major,
            'version.minor': minor,
            'version.patch': patch,
            'version.build': '123456789',
            'version.raw': '{}+123456789'.format(VSPHERE_VERSION),
        }
        datadog_agent.assert_metadata('test:123', version_metadata)