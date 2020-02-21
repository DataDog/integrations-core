# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging

import pytest
from pyVmomi import vim

from datadog_checks.vsphere.api_rest import VSphereRestAPI
from datadog_checks.vsphere.config import VSphereConfig

logger = logging.getLogger()


@pytest.mark.usefixtures("mock_rest_api")
def test_get_resource_tags(realtime_instance):

    config = VSphereConfig(realtime_instance, logger)
    mock_api = VSphereRestAPI(config, log=logger)
    resource_tags = mock_api.get_resource_tags()

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
