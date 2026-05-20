# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Unit tests for TUFPointerDownloader (v2 repository format)."""

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from datadog_checks.downloader.download_v2 import TUFPointerDownloader
from datadog_checks.downloader.exceptions import DigestMismatch, TargetNotFoundError

_PROJECT = 'datadog-postgres'
_VERSION = '14.0.0'
_WHEEL_CONTENT = b'fake wheel bytes for testing'
_WHEEL_DIGEST = hashlib.sha256(_WHEEL_CONTENT).hexdigest()
_WHEEL_LENGTH = len(_WHEEL_CONTENT)
_REPO_URL = 'https://agent-integration-wheels-staging.s3.amazonaws.com'

_POINTER = {
    'digest': _WHEEL_DIGEST,
    'length': _WHEEL_LENGTH,
    'version': _VERSION,
    'repository': _REPO_URL,
    'wheel_path': f'/wheels/{_PROJECT}/datadog_postgres-{_VERSION}-py3-none-any.whl',
    'attestation_path': f'/attestations/{_PROJECT}/{_VERSION}.sigstore.json',
}


def _mock_tuf_updater(pointer: dict) -> MagicMock:
    """Return an Updater mock that writes *pointer* as target content."""
    pointer_bytes = json.dumps(pointer).encode()
    mock_updater = MagicMock()
    mock_updater.get_targetinfo.return_value = MagicMock()

    def fake_download_target(_target_info, dest_path):
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
        Path(dest_path).write_bytes(pointer_bytes)

    mock_updater.download_target.side_effect = fake_download_target
    return mock_updater


def _mock_response(content: bytes) -> MagicMock:
    response = MagicMock()
    response.__enter__ = lambda s: s
    response.__exit__ = MagicMock(return_value=False)
    response.read.return_value = content
    return response


@pytest.fixture
def mock_urlopen():
    with patch('datadog_checks.downloader.download_v2.urllib.request.urlopen') as mock:
        mock.return_value = _mock_response(_WHEEL_CONTENT)
        yield mock


@pytest.fixture
def mock_updater_cls():
    with patch('datadog_checks.downloader.download_v2.Updater') as mock:
        mock.return_value = _mock_tuf_updater(_POINTER)
        yield mock


class TestTargetPath:
    def test_explicit_version_uses_versioned_pointer(self):
        assert TUFPointerDownloader._target_path(_PROJECT, '1.0.0') == f'{_PROJECT}/1.0.0.json'

    def test_missing_version_uses_latest_pointer(self):
        assert TUFPointerDownloader._target_path(_PROJECT, None) == f'{_PROJECT}/latest.json'


@pytest.mark.offline
class TestHappyPath:
    def test_download_returns_wheel_path(self, mock_urlopen, mock_updater_cls, tmp_path):
        downloader = TUFPointerDownloader(repository_url=_REPO_URL)
        wheel_path = downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)

        assert wheel_path.exists()
        assert wheel_path.read_bytes() == _WHEEL_CONTENT
        assert wheel_path.name == f'datadog_postgres-{_VERSION}-py3-none-any.whl'

    def test_repository_flag_overrides_pointer_repository(self, mock_urlopen, mock_updater_cls, tmp_path):
        prod_pointer = {**_POINTER, 'repository': 'https://agent-integration-wheels-prod.s3.amazonaws.com'}
        mock_updater_cls.return_value = _mock_tuf_updater(prod_pointer)

        downloader = TUFPointerDownloader(repository_url=_REPO_URL)
        downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)

        mock_urlopen.assert_called_once_with(
            f'{_REPO_URL}/wheels/{_PROJECT}/datadog_postgres-{_VERSION}-py3-none-any.whl'
        )

    def test_version_none_fetches_latest_pointer(self, mock_urlopen, mock_updater_cls, tmp_path):
        downloader = TUFPointerDownloader(repository_url=_REPO_URL)
        downloader.download(_PROJECT, dest_dir=tmp_path)

        mock_updater = mock_updater_cls.return_value
        assert mock_updater.get_targetinfo.call_args[0][0] == f'{_PROJECT}/latest.json'


@pytest.mark.offline
class TestTargetNotFound:
    def test_raises_when_tuf_target_absent(self, mock_urlopen, mock_updater_cls):
        mock_updater = MagicMock()
        mock_updater.get_targetinfo.return_value = None
        mock_updater_cls.return_value = mock_updater

        downloader = TUFPointerDownloader(repository_url=_REPO_URL)
        with pytest.raises(TargetNotFoundError, match=_PROJECT):
            downloader.get_pointer(_PROJECT, version='99.99.99')


@pytest.mark.offline
class TestDigestMismatch:
    def test_raises_on_corrupted_wheel(self, mock_urlopen, mock_updater_cls, tmp_path):
        mock_urlopen.return_value = _mock_response(b'tampered bytes')

        downloader = TUFPointerDownloader(repository_url=_REPO_URL)
        with pytest.raises(DigestMismatch, match=_PROJECT):
            downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)

    def test_raises_on_length_mismatch(self, mock_urlopen, mock_updater_cls, tmp_path):
        bad_pointer = {**_POINTER, 'length': _WHEEL_LENGTH + 1}
        mock_updater_cls.return_value = _mock_tuf_updater(bad_pointer)

        downloader = TUFPointerDownloader(repository_url=_REPO_URL)
        with pytest.raises(DigestMismatch, match='length'):
            downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)


@pytest.mark.offline
class TestDisableVerification:
    def test_directly_downloads_wheel_without_tuf_or_digest_checks(self, mock_urlopen, tmp_path):
        content = b'bytes not matching any signed pointer'
        mock_urlopen.return_value = _mock_response(content)

        with patch('datadog_checks.downloader.download_v2.Updater') as mock_updater_cls:
            downloader = TUFPointerDownloader(repository_url=_REPO_URL, disable_verification=True)
            wheel_path = downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)

        mock_urlopen.assert_called_once_with(
            f'{_REPO_URL}/wheels/{_PROJECT}/datadog_postgres-{_VERSION}-py3-none-any.whl'
        )
        assert wheel_path.name == f'datadog_postgres-{_VERSION}-py3-none-any.whl'
        assert wheel_path.read_bytes() == content
        mock_updater_cls.assert_not_called()

    def test_direct_download_requires_explicit_version(self, tmp_path):
        downloader = TUFPointerDownloader(repository_url=_REPO_URL, disable_verification=True)
        with pytest.raises(TargetNotFoundError, match='requires an explicit --version'):
            downloader.download(_PROJECT, dest_dir=tmp_path)
