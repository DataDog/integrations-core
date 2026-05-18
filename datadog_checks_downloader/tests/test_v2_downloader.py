# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Unit tests for TUFPointerDownloader (v2 repository format).

All tests are offline: the TUF Updater and HTTP calls are mocked so that no
network traffic is needed.
"""

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from datadog_checks.downloader.download_v2 import TUFPointerDownloader
from datadog_checks.downloader.exceptions import DigestMismatch, TargetNotFoundError

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_PROJECT = 'datadog-postgres'
_VERSION = '14.0.0'
_WHEEL_CONTENT = b'fake wheel bytes for testing'
_WHEEL_DIGEST = hashlib.sha256(_WHEEL_CONTENT).hexdigest()
_WHEEL_LENGTH = len(_WHEEL_CONTENT)

_POINTER = {
    'digest': _WHEEL_DIGEST,
    'length': _WHEEL_LENGTH,
    'version': _VERSION,
    'repository': 'https://agent-integration-wheels-staging.s3.amazonaws.com',
    'wheel_path': f'/wheels/{_PROJECT}/datadog_postgres-{_VERSION}-py3-none-any.whl',
    'attestation_path': f'/attestations/{_PROJECT}/{_VERSION}.sigstore.json',
}

_REPO_URL = 'https://agent-integration-wheels-staging.s3.amazonaws.com'


def _mock_tuf_updater(pointer: dict) -> MagicMock:
    """Return a mock Updater that yields *pointer* as the target content."""
    pointer_bytes = json.dumps(pointer).encode()
    mock_updater = MagicMock()
    mock_updater.get_targetinfo.return_value = MagicMock()

    def fake_download_target(_target_info, dest_path):
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
        Path(dest_path).write_bytes(pointer_bytes)

    mock_updater.download_target.side_effect = fake_download_target
    return mock_updater


# ---------------------------------------------------------------------------
# target-path unit tests
# ---------------------------------------------------------------------------


class TestTargetPath:
    def test_explicit_version_uses_versioned_pointer(self):
        assert TUFPointerDownloader._target_path(_PROJECT, '1.0.0') == f'{_PROJECT}/1.0.0.json'

    def test_missing_version_uses_latest_pointer(self):
        assert TUFPointerDownloader._target_path(_PROJECT, None) == f'{_PROJECT}/latest.json'


# ---------------------------------------------------------------------------
# Happy-path integration tests
# ---------------------------------------------------------------------------


@pytest.mark.offline
class TestHappyPath:
    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_download_returns_wheel_path(self, mock_urlopen, mock_updater_cls, tmp_path):
        mock_updater_cls.return_value = _mock_tuf_updater(_POINTER)

        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value.read.return_value = _WHEEL_CONTENT

        downloader = TUFPointerDownloader(repository_url=_REPO_URL)
        wheel_path = downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)

        assert wheel_path.exists()
        assert wheel_path.read_bytes() == _WHEEL_CONTENT
        assert wheel_path.name == f'datadog_postgres-{_VERSION}-py3-none-any.whl'

    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_repository_flag_overrides_pointer_repository(self, mock_urlopen, mock_updater_cls, tmp_path):
        """--repository supersedes the repository field baked into the pointer."""
        staging_url = 'https://agent-integration-wheels-staging.s3.amazonaws.com'
        prod_pointer = {**_POINTER, 'repository': 'https://agent-integration-wheels-prod.s3.amazonaws.com'}
        mock_updater_cls.return_value = _mock_tuf_updater(prod_pointer)

        captured_urls: list[str] = []

        def fake_urlopen(url):
            captured_urls.append(url)
            mock_resp = MagicMock()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.read.return_value = _WHEEL_CONTENT
            return mock_resp

        mock_urlopen.side_effect = fake_urlopen

        downloader = TUFPointerDownloader(repository_url=staging_url)
        downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)

        wheel_fetch_url = captured_urls[-1]
        assert wheel_fetch_url.startswith(staging_url), (
            f'Expected wheel fetch from {staging_url!r}, got {wheel_fetch_url!r}'
        )

    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_version_none_fetches_latest_pointer(self, mock_urlopen, mock_updater_cls, tmp_path):
        """version=None fetches <project>/latest.json."""
        mock_updater = _mock_tuf_updater(_POINTER)
        mock_updater_cls.return_value = mock_updater

        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value.read.return_value = _WHEEL_CONTENT

        downloader = TUFPointerDownloader(repository_url=_REPO_URL)
        downloader.download(_PROJECT, dest_dir=tmp_path)

        call_args = mock_updater.get_targetinfo.call_args[0][0]
        assert call_args == f'{_PROJECT}/latest.json'


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


@pytest.mark.offline
class TestTargetNotFound:
    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_raises_when_tuf_target_absent(self, mock_urlopen, mock_updater_cls, tmp_path):
        mock_updater = MagicMock()
        mock_updater.get_targetinfo.return_value = None
        mock_updater_cls.return_value = mock_updater

        downloader = TUFPointerDownloader(repository_url=_REPO_URL)
        with pytest.raises(TargetNotFoundError, match=_PROJECT):
            downloader.get_pointer(_PROJECT, version='99.99.99')


@pytest.mark.offline
class TestDigestMismatch:
    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_raises_on_corrupted_wheel(self, mock_urlopen, mock_updater_cls, tmp_path):
        mock_updater_cls.return_value = _mock_tuf_updater(_POINTER)

        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value.read.return_value = b'tampered bytes'

        downloader = TUFPointerDownloader(repository_url=_REPO_URL)
        with pytest.raises(DigestMismatch, match=_PROJECT):
            downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)

    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_raises_on_length_mismatch(self, mock_urlopen, mock_updater_cls, tmp_path):
        bad_pointer = {**_POINTER, 'length': _WHEEL_LENGTH + 1}
        mock_updater_cls.return_value = _mock_tuf_updater(bad_pointer)

        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value.read.return_value = _WHEEL_CONTENT

        downloader = TUFPointerDownloader(repository_url=_REPO_URL)
        with pytest.raises(DigestMismatch, match='length'):
            downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)


# ---------------------------------------------------------------------------
# Disable-verification mode
# ---------------------------------------------------------------------------


@pytest.mark.offline
class TestDisableVerification:
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_directly_downloads_wheel_without_tuf_or_digest_checks(self, mock_urlopen, tmp_path):
        """disable_verification bypasses TUF/pointers and downloads the wheel by
        convention from /wheels/<project>/<wheel>.whl."""
        captured_urls: list[str] = []

        def fake_urlopen(url):
            captured_urls.append(url)
            mock_resp = MagicMock()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.read.return_value = b'bytes not matching any signed pointer'
            return mock_resp

        mock_urlopen.side_effect = fake_urlopen

        with patch('datadog_checks.downloader.download_v2.Updater') as mock_updater_cls:
            downloader = TUFPointerDownloader(repository_url=_REPO_URL, disable_verification=True)
            wheel_path = downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)

        assert captured_urls == [
            f'{_REPO_URL}/wheels/{_PROJECT}/datadog_postgres-{_VERSION}-py3-none-any.whl',
        ]
        assert wheel_path.name == f'datadog_postgres-{_VERSION}-py3-none-any.whl'
        assert wheel_path.read_bytes() == b'bytes not matching any signed pointer'
        mock_updater_cls.assert_not_called()

    def test_direct_download_requires_explicit_version(self, tmp_path):
        downloader = TUFPointerDownloader(repository_url=_REPO_URL, disable_verification=True)
        with pytest.raises(TargetNotFoundError, match='requires an explicit --version'):
            downloader.download(_PROJECT, dest_dir=tmp_path)
