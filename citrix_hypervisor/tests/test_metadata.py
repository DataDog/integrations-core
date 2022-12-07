# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import mock
import pytest

from datadog_checks.citrix_hypervisor import CitrixHypervisorCheck

from . import common


@pytest.mark.usefixtures('mock_responses')
def test_collect_metadata(datadog_agent, instance):
    check = CitrixHypervisorCheck('citrix_hypervisor', {}, [instance])
    check.check_id = 'test:123'
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': '8',
        'version.minor': '2',
        'version.patch': '0',
        'version.raw': '8.2.0',
    }

    with open(os.path.join(common.HERE, 'fixtures', 'standalone', 'version.json'), 'rb') as f:
        content = json.load(f)

        xenserver = common.mocked_xenserver('master')
        xenserver.session.get_this_host.return_value = {'Status': 'Success', 'Value': 'hostref'}
        xenserver.host.get_software_version.return_value = content

        with mock.patch('six.moves.xmlrpc_client.Server', return_value=xenserver):
            check.check(None)
            datadog_agent.assert_metadata('test:123', version_metadata)
            datadog_agent.assert_metadata_count(len(version_metadata))
