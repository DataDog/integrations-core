# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Unit tests for TUFPointerDownloader (v2 repository format).

All tests are offline: the TUF Updater and HTTP calls are mocked so that no
network traffic is needed.  The tests verify the business logic of
``TUFPointerDownloader`` — TUF delegation, pointer parsing, wheel fetch, and
digest verification — without exercising tuf.ngclient internals.
"""

import hashlib
import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from datadog_checks.downloader.download_v2 import TUFPointerDownloader
from datadog_checks.downloader.exceptions import DigestMismatch, TargetNotFoundError

# ---------------------------------------------------------------------------
# Shared test fixtures
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


def _mock_tuf_updater(pointer: dict):
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
# Happy-path tests
# ---------------------------------------------------------------------------


@pytest.mark.offline
class TestHappyPath:
    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_download_returns_wheel_path(self, mock_urlopen, mock_updater_cls, tmp_path):
        """Successful download writes the wheel and returns its path."""
        mock_updater_cls.return_value = _mock_tuf_updater(_POINTER)

        # Wheel HTTP response
        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value.read.return_value = _WHEEL_CONTENT

        # Bootstrap root.json from trust anchor
        trust_anchor = tmp_path / 'root.json'
        trust_anchor.write_text('{}')

        downloader = TUFPointerDownloader(
            repository_url=_REPO_URL, trust_anchor=trust_anchor
        )
        wheel_path = downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)

        assert wheel_path.exists()
        assert wheel_path.read_bytes() == _WHEEL_CONTENT
        assert wheel_path.name == f'datadog_postgres-{_VERSION}-py3-none-any.whl'

    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_get_pointer_returns_dict(self, mock_urlopen, mock_updater_cls, tmp_path):
        """get_pointer returns the parsed JSON without downloading the wheel."""
        mock_updater_cls.return_value = _mock_tuf_updater(_POINTER)

        trust_anchor = tmp_path / 'root.json'
        trust_anchor.write_text('{}')

        downloader = TUFPointerDownloader(
            repository_url=_REPO_URL, trust_anchor=trust_anchor
        )
        pointer = downloader.get_pointer(_PROJECT, version=_VERSION)

        assert pointer['version'] == _VERSION
        assert pointer['digest'] == _WHEEL_DIGEST
        assert pointer['wheel_path'] == f'/wheels/{_PROJECT}/datadog_postgres-{_VERSION}-py3-none-any.whl'

    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_latest_resolves_to_latest_json(self, mock_urlopen, mock_updater_cls, tmp_path):
        """version=None uses targets/<project>/latest.json."""
        target_path = f'{_PROJECT}/latest.json'
        mock_updater = _mock_tuf_updater(_POINTER)
        mock_updater_cls.return_value = mock_updater

        trust_anchor = tmp_path / 'root.json'
        trust_anchor.write_text('{}')
        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value.read.return_value = _WHEEL_CONTENT

        downloader = TUFPointerDownloader(
            repository_url=_REPO_URL, trust_anchor=trust_anchor
        )
        downloader.download(_PROJECT, dest_dir=tmp_path)

        mock_updater.get_targetinfo.assert_called_once_with(target_path)


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


@pytest.mark.offline
class TestTargetNotFound:
    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_raises_when_tuf_target_absent(self, mock_urlopen, mock_updater_cls, tmp_path):
        """TargetNotFoundError is raised when TUF has no entry for the target."""
        mock_updater = MagicMock()
        mock_updater.get_targetinfo.return_value = None  # not in TUF metadata
        mock_updater_cls.return_value = mock_updater

        trust_anchor = tmp_path / 'root.json'
        trust_anchor.write_text('{}')

        downloader = TUFPointerDownloader(
            repository_url=_REPO_URL, trust_anchor=trust_anchor
        )
        with pytest.raises(TargetNotFoundError, match=_PROJECT):
            downloader.get_pointer(_PROJECT, version='99.99.99')


@pytest.mark.offline
class TestDigestMismatch:
    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_raises_on_corrupted_wheel(self, mock_urlopen, mock_updater_cls, tmp_path):
        """DigestMismatch is raised when the downloaded wheel has a wrong sha256."""
        mock_updater_cls.return_value = _mock_tuf_updater(_POINTER)

        # Return tampered bytes whose digest won't match the pointer
        tampered = b'this is not the real wheel'
        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value.read.return_value = tampered

        trust_anchor = tmp_path / 'root.json'
        trust_anchor.write_text('{}')

        downloader = TUFPointerDownloader(
            repository_url=_REPO_URL, trust_anchor=trust_anchor
        )
        with pytest.raises(DigestMismatch, match=_PROJECT):
            downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)

    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_raises_on_length_mismatch(self, mock_urlopen, mock_updater_cls, tmp_path):
        """DigestMismatch is raised when the byte length differs from the pointer."""
        # Pointer with wrong length
        bad_pointer = {**_POINTER, 'length': _WHEEL_LENGTH + 1}
        mock_updater_cls.return_value = _mock_tuf_updater(bad_pointer)

        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value.read.return_value = _WHEEL_CONTENT

        trust_anchor = tmp_path / 'root.json'
        trust_anchor.write_text('{}')

        downloader = TUFPointerDownloader(
            repository_url=_REPO_URL, trust_anchor=trust_anchor
        )
        with pytest.raises(DigestMismatch, match='length'):
            downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)


# ---------------------------------------------------------------------------
# Disable-verification mode tests
# ---------------------------------------------------------------------------


@pytest.mark.offline
class TestDisableVerification:
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_skips_tuf_and_digest(self, mock_urlopen, tmp_path):
        """With disable_verification, no Updater is created and digest is not checked."""
        pointer_bytes = json.dumps(_POINTER).encode()

        call_count = [0]

        def fake_urlopen(url):
            call_count[0] += 1
            mock_resp = MagicMock()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            if 'targets' in url and url.endswith('.json'):
                mock_resp.read.return_value = pointer_bytes
            else:
                mock_resp.read.return_value = _WHEEL_CONTENT
            return mock_resp

        mock_urlopen.side_effect = fake_urlopen

        downloader = TUFPointerDownloader(
            repository_url=_REPO_URL, disable_verification=True
        )
        # Use deliberately wrong digest in pointer — should not raise
        bad_pointer = {**_POINTER, 'digest': 'deadbeef' * 8}
        pointer_bytes = json.dumps(bad_pointer).encode()

        wheel_path = downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)
        assert wheel_path.exists()

    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_not_found_via_http_404(self, mock_urlopen):
        """TargetNotFoundError is raised on HTTP 404 in disable_verification mode."""
        http_404 = urllib.error.HTTPError(
            url='https://example.com/targets/datadog-postgres/99.0.0.json',
            code=404,
            msg='Not Found',
            hdrs=MagicMock(),
            fp=None,
        )
        mock_urlopen.side_effect = http_404

        downloader = TUFPointerDownloader(
            repository_url=_REPO_URL, disable_verification=True
        )
        with pytest.raises(TargetNotFoundError):
            downloader.get_pointer(_PROJECT, version='99.0.0')
