# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import logging

import pytest
from mock import MagicMock, patch
from pyVmomi import vim

from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.api_rest import VSphereRestAPI
from datadog_checks.vsphere.config import VSphereConfig

from .common import build_rest_api_client

logger = logging.getLogger()


@pytest.mark.usefixtures("mock_rest_api", "mock_type")
def test_get_resource_tags(realtime_instance):
    config = VSphereConfig(realtime_instance, {}, logger)
    mock_api = build_rest_api_client(config, logger)
    mock_mors = [MagicMock(spec=vim.VirtualMachine, _moId="foo")]

    resource_tags = mock_api.get_resource_tags_for_mors(mock_mors)

    expected_resource_tags = {
        vim.HostSystem: {'10.0.0.104-1': ['my_cat_name_2:my_tag_name_2']},
        vim.VirtualMachine: {'VM4-4-1': ['my_cat_name_1:my_tag_name_1', 'my_cat_name_2:my_tag_name_2']},
        vim.Datacenter: {},
        vim.Datastore: {'NFS-Share-1': ['my_cat_name_2:my_tag_name_2']},
        vim.ClusterComputeResource: {},
    }
    assert expected_resource_tags == resource_tags


@pytest.mark.usefixtures("mock_rest_api", "mock_type", "mock_api", "mock_threadpool")
def test_tagging_tags_get_exception(realtime_instance, dd_run_check, caplog, aggregator):

    instance = copy.deepcopy(realtime_instance)
    instance['collect_tags'] = True
    instance['excluded_host_tags'] = ['my_cat_name_1']
    check = VSphereCheck('vsphere', {}, [instance])

    with patch('datadog_checks.vsphere.api_rest.VSphereRestClient.tagging_tags_get', side_effect=Exception("test")):
        dd_run_check(check)
        assert "Exception in get_tags for `tag_id_1`: test" in caplog.text
        assert "Result resource tags: {<class 'pyVmomi.VmomiSupport.vim.VirtualMachine'>: "
        "defaultdict(<class 'list'>, {}), <class 'pyVmomi.VmomiSupport.vim.HostSystem'>: "
        "defaultdict(<class 'list'>, {}), <class 'pyVmomi.VmomiSupport.vim.Datacenter'>: "
        "defaultdict(<class 'list'>, {}), <class 'pyVmomi.VmomiSupport.vim.Datastore'>: "
        "defaultdict(<class 'list'>, {}), <class 'pyVmomi.VmomiSupport.vim.ClusterComputeResource'>: "
        "defaultdict(<class 'list'>, {})}" in caplog.text

        aggregator.assert_metric_has_tag('vsphere.net.bytesTx.avg', 'my_cat_name_1:my_tag_name_1', count=0)


@pytest.mark.usefixtures("mock_rest_api", "mock_type", "mock_api", "mock_threadpool")
def test_tagging_category_get_exception(realtime_instance, dd_run_check, caplog, aggregator):

    instance = copy.deepcopy(realtime_instance)
    instance['collect_tags'] = True
    instance['excluded_host_tags'] = ['my_cat_name_1']
    check = VSphereCheck('vsphere', {}, [instance])

    with patch('datadog_checks.vsphere.api_rest.VSphereRestClient.tagging_category_get', side_effect=Exception("test")):
        dd_run_check(check)
        assert "Exception in get_tags for `tag_id_1`: test" in caplog.text
        assert "Result resource tags: {<class 'pyVmomi.VmomiSupport.vim.VirtualMachine'>: "
        "defaultdict(<class 'list'>, {}), <class 'pyVmomi.VmomiSupport.vim.HostSystem'>: "
        "defaultdict(<class 'list'>, {}), <class 'pyVmomi.VmomiSupport.vim.Datacenter'>: "
        "defaultdict(<class 'list'>, {}), <class 'pyVmomi.VmomiSupport.vim.Datastore'>: "
        "defaultdict(<class 'list'>, {}), <class 'pyVmomi.VmomiSupport.vim.ClusterComputeResource'>: "
        "defaultdict(<class 'list'>, {})}" in caplog.text

        aggregator.assert_metric_has_tag('vsphere.net.bytesTx.avg', 'my_cat_name_1:my_tag_name_1', count=0)


@pytest.mark.usefixtures("mock_rest_api", "mock_type", "mock_threadpool", "mock_api")
def test_get_tags_log(realtime_instance, dd_run_check, caplog, aggregator):

    instance = copy.deepcopy(realtime_instance)
    instance['collect_tags'] = True
    instance['excluded_host_tags'] = ['my_cat_name_1']

    check = VSphereCheck('vsphere', {}, [instance])

    dd_run_check(check)
    assert "Result resource tags: {<class 'pyVmomi.VmomiSupport.vim.VirtualMachine'>: "
    "defaultdict(<class 'list'>, {'VM4-4-1': ['my_cat_name_1:my_tag_name_1', "
    "'my_cat_name_2:my_tag_name_2']})" in caplog.text

    aggregator.assert_metric_has_tag('vsphere.net.bytesTx.avg', 'my_cat_name_1:my_tag_name_1')


@pytest.mark.parametrize(
    'init_config, instance_config, expected_shared_rest_api_options, expected_rest_api_options',
    [
        pytest.param(
            {},
            {
                'username': 'my-username',
                'password': 'my-password',
            },
            {},
            {
                'username': 'my-username',
                'password': 'my-password',
                'tls_ca_cert': None,
                'tls_ignore_warning': False,
                'tls_verify': True,
            },
            id='no rest_api_options',
        ),
        pytest.param(
            {},
            {
                'username': 'my-username',
                'password': 'my-password',
                'ssl_capath': 'abc123',
                'ssl_verify': False,
                'tls_ignore_warning': True,
            },
            {},
            {
                'username': 'my-username',
                'password': 'my-password',
                'tls_ca_cert': 'abc123',
                'tls_ignore_warning': True,
                'tls_verify': False,
            },
            id='existing options rest_api_options',
        ),
        pytest.param(
            {
                'rest_api_options': {
                    'timeout': 15,
                }
            },
            {
                'username': 'my-username',
                'password': 'my-password',
            },
            {
                'timeout': 15,
            },
            {
                'username': 'my-username',
                'password': 'my-password',
                'tls_ca_cert': None,
                'tls_ignore_warning': False,
                'tls_verify': True,
            },
            id='init rest_api_options',
        ),
        pytest.param(
            {},
            {
                'username': 'my-username',
                'password': 'my-password',
                'rest_api_options': {
                    'timeout': 15,
                },
            },
            {},
            {
                'username': 'my-username',
                'password': 'my-password',
                'tls_ca_cert': None,
                'tls_ignore_warning': False,
                'tls_verify': True,
                'timeout': 15,
            },
            id='instance rest_api_options',
        ),
        pytest.param(
            {},
            {
                'username': 'my-username',
                'password': 'my-password',
                'rest_api_options': {
                    'timeout': 15,
                },
            },
            {},
            {
                'username': 'my-username',
                'password': 'my-password',
                'tls_ca_cert': None,
                'tls_ignore_warning': False,
                'tls_verify': True,
                'timeout': 15,
            },
            id='instance rest_api_options',
        ),
        pytest.param(
            {},
            {
                'username': 'my-username',
                'password': 'my-password',
                'rest_api_options': {
                    'timeout': 15,
                    'username': 'my-username2',
                    'password': 'my-password2',
                    'tls_ca_cert': 'abc',
                    'tls_ignore_warning': True,
                    'tls_verify': False,
                },
            },
            {},
            {
                'username': 'my-username2',
                'password': 'my-password2',
                'tls_ca_cert': 'abc',
                'tls_ignore_warning': True,
                'tls_verify': False,
                'timeout': 15,
            },
            id='rest_api_options has precedence',
        ),
    ],
)
def test_rest_api_config(init_config, instance_config, expected_shared_rest_api_options, expected_rest_api_options):
    instance_config.update(
        {
            'name': 'abc',
            'use_legacy_check_version': False,
            'host': 'my-host',
        }
    )
    check = VSphereCheck('vsphere', init_config, [instance_config])

    assert check._config.rest_api_options == expected_rest_api_options
    assert check._config.shared_rest_api_options == expected_shared_rest_api_options


@pytest.mark.usefixtures("mock_rest_api")
def test_create_session(realtime_instance):
    config = VSphereConfig(realtime_instance, {}, logger)
    mock_api = build_rest_api_client(config, logger)

    assert mock_api._client._http.options['headers']['vmware-api-session-id'] == "dummy-token"


@pytest.mark.usefixtures("mock_rest_api")
@pytest.mark.parametrize(("batch_size", "number_of_batches"), [(25, 40), (100, 10), (101, 10)])
def test_make_batch(realtime_instance, batch_size, number_of_batches):
    realtime_instance['batch_tags_collector_size'] = batch_size
    config = VSphereConfig(realtime_instance, {}, logger)
    mock_api = build_rest_api_client(config, logger)
    data_to_batch = list(range(1000))

    batches = list(VSphereRestAPI.make_batch(mock_api, data_to_batch))
    flat_data = [x for y in batches for x in y]
    assert flat_data == data_to_batch
    assert len(batches) == number_of_batches
