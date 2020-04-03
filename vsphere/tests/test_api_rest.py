# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging

import pytest
from mock import MagicMock
from pyVmomi import vim

from datadog_checks.vsphere.api_rest import VSphereRestAPI
from datadog_checks.vsphere.config import VSphereConfig

logger = logging.getLogger()


@pytest.mark.usefixtures("mock_rest_api", "mock_type")
def test_get_resource_tags(realtime_instance):
    config = VSphereConfig(realtime_instance, logger)
    mock_api = VSphereRestAPI(config, log=logger)
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


@pytest.mark.usefixtures("mock_rest_api")
def test_create_session(realtime_instance):
    config = VSphereConfig(realtime_instance, logger)
    mock_api = VSphereRestAPI(config, log=logger)

    assert mock_api._client._http.options['headers']['vmware-api-session-id'] == "dummy-token"


@pytest.mark.usefixtures("mock_rest_api")
@pytest.mark.parametrize(("batch_size", "number_of_batches"), [(25, 40), (100, 10), (101, 10)])
def test_make_batch(realtime_instance, batch_size, number_of_batches):
    realtime_instance['batch_tags_collector_size'] = batch_size
    config = VSphereConfig(realtime_instance, logger)
    mock_api = VSphereRestAPI(config, log=logger)
    data_to_batch = list(range(1000))

    batches = list(VSphereRestAPI.make_batch(mock_api, data_to_batch))
    flat_data = [x for y in batches for x in y]
    assert flat_data == data_to_batch
    assert len(batches) == number_of_batches
