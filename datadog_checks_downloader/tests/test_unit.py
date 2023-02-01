# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from unittest.mock import patch
from datadog_checks.downloader.download import get_wheel_relpath

mocked_wheels = {'3.6.1': {'py2.py3': 'datadog_vsphere-3.6.1-py2.py3-none-any.whl'}, '5.4.0rc2': {'py2.py3': 'datadog_vsphere-5.4.0rc2-py2.py3-none-any.whl'}, '6.2.2a1': {'py2.py3': 'datadog_vsphere-6.2.2b1-py2.py3-none-any.whl'}, '6.3.0b1': {'py2.py3': 'datadog_vsphere-6.3.0b1-py2.py3-none-any.whl'}}
@patch('datadog_checks.downloader.download.wheels', mocked_wheels)
def test_non_official_wheel_filter():
    integration = "datadog-vsphere"
    result = get_wheel_relpath(integration)
    assert result == 'simple/datadog-vsphere/datadog_vsphere-3.6.1-py2.py3-none-any.whl'
