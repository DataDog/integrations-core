# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import urllib.error

import pytest
import requests
from in_toto.exceptions import LinkNotFoundError
from tuf.api.exceptions import (
    DownloadError,
    DownloadHTTPError,
    DownloadLengthMismatchError,
    ExpiredMetadataError,
    LengthOrHashMismatchError,
    SlowRetrievalError,
    UnsignedMetadataError,
)

from datadog_checks.downloader.cli import download_error_category
from datadog_checks.downloader.download import TUFDownloader
from datadog_checks.downloader.exceptions import (
    DigestMismatch,
    DuplicatePackage,
    InconsistentSimpleIndex,
    IncorrectRootLayoutType,
    LengthMismatch,
    MalformedPointerError,
    MissingVersions,
    NoInTotoLinkMetadataFound,
    NonDatadogPackage,
    NoSuchDatadogPackage,
    NoSuchDatadogPackageVersion,
    PythonVersionMismatch,
    TargetNotFoundError,
)


def _http_error(status_code: int) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status_code
    return requests.HTTPError(response=response)


@pytest.mark.parametrize(
    'exc,expected',
    [
        pytest.param(TargetNotFoundError('missing'), 'not_found', id='v2-target-not-found'),
        pytest.param(NoSuchDatadogPackage('datadog-x'), 'not_found', id='v1-no-such-package'),
        pytest.param(NoSuchDatadogPackageVersion('datadog-x', '1.0.0'), 'not_found', id='v1-no-such-version'),
        pytest.param(MissingVersions('datadog-x'), 'not_found', id='v1-no-versions'),
        pytest.param(_http_error(404), 'not_found', id='unverified-v2-wheel-404'),
        pytest.param(urllib.error.HTTPError('u', 404, 'Not Found', {}, None), 'not_found', id='unverified-v1-404'),
        pytest.param(DownloadError('boom'), 'network', id='tuf-download-error'),
        pytest.param(DownloadHTTPError('boom', 404), 'network', id='tuf-metadata-404'),
        pytest.param(SlowRetrievalError(), 'network', id='tuf-slow-retrieval'),
        pytest.param(requests.exceptions.ConnectionError('unreachable'), 'network', id='requests-connection'),
        pytest.param(_http_error(503), 'network', id='wheel-503'),
        pytest.param(urllib.error.URLError('unreachable'), 'network', id='urllib-url-error'),
        pytest.param(TimeoutError('slow'), 'network', id='timeout'),
        pytest.param(DigestMismatch('datadog-x', 'a', 'b'), 'integrity', id='digest-mismatch'),
        pytest.param(LengthMismatch('datadog-x', 1, 2), 'integrity', id='length-mismatch'),
        pytest.param(MalformedPointerError('datadog-x', 'digest'), 'integrity', id='malformed-pointer'),
        pytest.param(LengthOrHashMismatchError('boom'), 'integrity', id='tuf-length-or-hash-mismatch'),
        pytest.param(DownloadLengthMismatchError('boom'), 'integrity', id='tuf-download-length-mismatch'),
        pytest.param(ExpiredMetadataError('expired'), 'metadata', id='tuf-expired'),
        pytest.param(UnsignedMetadataError('unsigned'), 'metadata', id='tuf-unsigned'),
        pytest.param(InconsistentSimpleIndex('a', 'b'), 'metadata', id='v1-inconsistent-index'),
        pytest.param(DuplicatePackage('datadog-x', '1.0.0', 'py3'), 'metadata', id='v1-duplicate-package'),
        pytest.param(NoInTotoLinkMetadataFound('simple/x.whl'), 'verification', id='in-toto-missing-links'),
        pytest.param(LinkNotFoundError('missing'), 'verification', id='in-toto-library'),
        pytest.param(NonDatadogPackage('requests'), 'other', id='non-datadog-package'),
        pytest.param(IncorrectRootLayoutType('core', 'extras'), 'other', id='incorrect-root-layout'),
        pytest.param(PythonVersionMismatch('datadog-x', '1.0.0', 'py3', {}), 'other', id='python-mismatch'),
        pytest.param(SystemExit(1), 'other', id='system-exit'),
        pytest.param(ValueError('bad pointer'), 'other', id='other'),
    ],
)
def test_download_error_category(exc, expected):
    assert download_error_category(exc) == expected


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
