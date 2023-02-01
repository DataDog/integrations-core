# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from unittest.mock import patch
from datadog_checks.downloader.download import TUFDownloader

def test_non_official_wheel_filter(mocker):
    mocked_wheels = {
        '3.6.1': {'py2.py3': 'datadog_vsphere-3.6.1-py2.py3-none-any.whl'},
        '5.4.0rc2': {'py2.py3': 'datadog_vsphere-5.4.0rc2-py2.py3-none-any.whl'},
        '6.2.2a1': {'py2.py3': 'datadog_vsphere-6.2.2b1-py2.py3-none-any.whl'},
        '6.3.0b1': {'py2.py3': 'datadog_vsphere-6.3.0b1-py2.py3-none-any.whl'}
    }
    
    downloader = TUFDownloader()
    mock_wheels_call = mocker.patch.object(TUFDownloader, '_TUFDownloader__get_versions', return_value=mocked_wheels)

    integration = "datadog-vsphere"
    result = downloader.get_wheel_relpath(integration)

    mock_wheels_call.assert_called_once()
    assert result == 'simple/datadog-vsphere/datadog_vsphere-3.6.1-py2.py3-none-any.whl'