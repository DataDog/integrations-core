# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import urllib.error

import pytest
from datadog_checks.downloader.cli import _v2_failure_category
from datadog_checks.downloader.download import TUFDownloader
from datadog_checks.downloader.exceptions import TargetNotFoundError
from tuf.api.exceptions import DownloadError


@pytest.mark.parametrize(
    'exc,expected',
    [
        pytest.param(TargetNotFoundError('missing'), 'target version not found', id='target-not-found'),
        pytest.param(urllib.error.URLError('timeout'), 'network error', id='network-urlerror'),
        pytest.param(DownloadError('boom'), 'network error', id='network-downloaderror'),
        pytest.param(TimeoutError('slow'), 'network error', id='network-timeout'),
        pytest.param(ValueError('bad pointer'), 'other', id='other'),
    ],
)
def test_v2_failure_category(exc, expected):
    assert _v2_failure_category(exc) == expected


def test_non_official_wheel_filter(mocker):
    mocked_wheels = {
        '3.6.1': {'py2.py3': 'datadog_vsphere-3.6.1-py2.py3-none-any.whl'},
        '3.6.2': {'py2.py3': 'datadog_vsphere-3.6.2-py2.py3-none-any.whl'},
        '5.4.0rc2': {'py2.py3': 'datadog_vsphere-5.4.0rc2-py2.py3-none-any.whl'},
        '6.2.2a1': {'py2.py3': 'datadog_vsphere-6.2.2b1-py2.py3-none-any.whl'},
        '6.3.0b1': {'py2.py3': 'datadog_vsphere-6.3.0b1-py2.py3-none-any.whl'},
        '6.3.0pre3': {'py2.py3': 'datadog_vsphere-6.3.0pre1-py2.py3-none-any.whl'},
    }

    downloader = TUFDownloader()
    mock_wheels_call = mocker.patch.object(TUFDownloader, '_TUFDownloader__get_versions', return_value=mocked_wheels)

    integration = "datadog-vsphere"
    result = downloader.get_wheel_relpath(integration)

    mock_wheels_call.assert_called_once()
    assert result == 'simple/datadog-vsphere/datadog_vsphere-3.6.2-py2.py3-none-any.whl'
