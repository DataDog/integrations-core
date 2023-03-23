import mock
import pytest

from datadog_checks.openstack_controller.api.api_rest import ApiRest
from datadog_checks.openstack_controller.api.api_sdk import ApiSdk
from datadog_checks.openstack_controller.api.factory import make_api
from datadog_checks.openstack_controller.config import OpenstackConfig

from .common import TEST_OPENSTACK_CONFIG_PATH

pytestmark = [pytest.mark.unit]


def test_make_api_rest():
    instance = {
        'keystone_server_url': 'http://10.164.0.83/identity',
        'user_name': 'admin',
        'user_password': 'password',
    }
    config = OpenstackConfig(mock.MagicMock(), instance)
    api = make_api(config, mock.MagicMock(), mock.MagicMock())
    assert isinstance(api, ApiRest)


def test_make_api_sdk():
    instance = {
        'openstack_cloud_name': 'test_cloud',
        'openstack_config_file_path': TEST_OPENSTACK_CONFIG_PATH,
    }
    config = OpenstackConfig(mock.MagicMock(), instance)
    api = make_api(config, mock.MagicMock(), mock.MagicMock())
    assert isinstance(api, ApiSdk)
