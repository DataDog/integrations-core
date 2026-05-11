# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Unit tests for TUFPointerDownloader (v2 repository format).

All tests are offline: the TUF Updater and HTTP calls are mocked so that no
network traffic is needed.
"""

import hashlib
import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version
from tuf.api.metadata import MetaFile, Snapshot, Targets, Timestamp

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


def _make_targets(*versions: str) -> Targets:
    """Build a Targets object listing the given versions for _PROJECT."""
    from tuf.api.metadata import TargetFile

    targets = Targets()
    for ver in versions:
        path = f'{_PROJECT}/{ver}.json'
        tf = MagicMock(spec=TargetFile)
        tf.hashes = {'sha256': 'a' * 64}
        tf.length = 100
        targets.targets[path] = tf
    return targets


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


def _patch_updater_and_targets(pointer: dict, targets: Targets):
    """Patch Updater and the targets metadata file read used by get_pointer."""
    mock_updater = _mock_tuf_updater(pointer)

    def fake_from_file(path):
        md = MagicMock()
        md.signed = targets
        return md

    return (
        patch('datadog_checks.downloader.download_v2.Updater', return_value=mock_updater),
        patch('datadog_checks.downloader.download_v2.Metadata', **{'__getitem__': MagicMock()}),
        patch('datadog_checks.downloader.download_v2.Path.glob', return_value=iter(['fake.targets.json'])),
        fake_from_file,
        mock_updater,
    )


# ---------------------------------------------------------------------------
# _resolve_version unit tests
# ---------------------------------------------------------------------------


class TestResolveVersion:
    def test_explicit_version_returned_unchanged(self):
        targets = _make_targets('1.0.0', '2.0.0')
        assert TUFPointerDownloader._resolve_version(_PROJECT, '1.0.0', targets) == '1.0.0'

    def test_latest_picks_highest_stable(self):
        targets = _make_targets('1.0.0', '2.0.0', '1.5.0')
        result = TUFPointerDownloader._resolve_version(_PROJECT, None, targets)
        assert result == '2.0.0'

    def test_latest_excludes_prereleases(self):
        targets = _make_targets('1.0.0', '2.0.0rc1', '1.9.0b2', '1.8.0a1', '1.7.0.dev1')
        result = TUFPointerDownloader._resolve_version(_PROJECT, None, targets)
        assert result == '1.0.0'

    def test_latest_includes_post_releases(self):
        targets = _make_targets('1.0.0', '1.0.0.post1')
        result = TUFPointerDownloader._resolve_version(_PROJECT, None, targets)
        assert result == '1.0.0.post1'

    def test_no_stable_versions_raises(self):
        targets = _make_targets('1.0.0rc1', '2.0.0b1')
        with pytest.raises(TargetNotFoundError, match=_PROJECT):
            TUFPointerDownloader._resolve_version(_PROJECT, None, targets)

    def test_ignores_other_projects(self):
        from tuf.api.metadata import TargetFile

        targets = Targets()
        for path in ['datadog-mysql/1.0.0.json', f'{_PROJECT}/2.0.0.json']:
            tf = MagicMock(spec=TargetFile)
            tf.hashes = {'sha256': 'a' * 64}
            tf.length = 100
            targets.targets[path] = tf

        result = TUFPointerDownloader._resolve_version(_PROJECT, None, targets)
        assert result == '2.0.0'


# ---------------------------------------------------------------------------
# Happy-path integration tests
# ---------------------------------------------------------------------------


@pytest.mark.offline
class TestHappyPath:
    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.Metadata')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_download_returns_wheel_path(self, mock_urlopen, mock_metadata_cls, mock_updater_cls, tmp_path):
        targets = _make_targets(_VERSION)
        mock_updater_cls.return_value = _mock_tuf_updater(_POINTER)
        mock_metadata_cls.__getitem__.return_value.from_file.return_value.signed = targets

        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value.read.return_value = _WHEEL_CONTENT

        with patch('datadog_checks.downloader.download_v2.Path.glob', return_value=iter(['1.targets.json'])):
            downloader = TUFPointerDownloader(repository_url=_REPO_URL)
            wheel_path = downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)

        assert wheel_path.exists()
        assert wheel_path.read_bytes() == _WHEEL_CONTENT
        assert wheel_path.name == f'datadog_postgres-{_VERSION}-py3-none-any.whl'

    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.Metadata')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_repository_flag_overrides_pointer_repository(self, mock_urlopen, mock_metadata_cls, mock_updater_cls, tmp_path):
        """--repository supersedes the repository field baked into the pointer."""
        staging_url = 'https://agent-integration-wheels-staging.s3.amazonaws.com'
        prod_pointer = {**_POINTER, 'repository': 'https://agent-integration-wheels-prod.s3.amazonaws.com'}
        targets = _make_targets(_VERSION)
        mock_updater_cls.return_value = _mock_tuf_updater(prod_pointer)
        mock_metadata_cls.__getitem__.return_value.from_file.return_value.signed = targets

        captured_urls: list[str] = []

        def fake_urlopen(url):
            captured_urls.append(url)
            mock_resp = MagicMock()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.read.return_value = _WHEEL_CONTENT
            return mock_resp

        mock_urlopen.side_effect = fake_urlopen

        with patch('datadog_checks.downloader.download_v2.Path.glob', return_value=iter(['1.targets.json'])):
            downloader = TUFPointerDownloader(repository_url=staging_url)
            downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)

        wheel_fetch_url = captured_urls[-1]
        assert wheel_fetch_url.startswith(staging_url), (
            f'Expected wheel fetch from {staging_url!r}, got {wheel_fetch_url!r}'
        )

    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.Metadata')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_version_none_resolves_to_latest_stable(self, mock_urlopen, mock_metadata_cls, mock_updater_cls, tmp_path):
        """version=None picks the highest stable version from N.targets.json."""
        targets = _make_targets('1.0.0', '2.0.0', '3.0.0rc1')
        mock_updater = _mock_tuf_updater(_POINTER)
        mock_updater_cls.return_value = mock_updater
        mock_metadata_cls.__getitem__.return_value.from_file.return_value.signed = targets

        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value.read.return_value = _WHEEL_CONTENT

        with patch('datadog_checks.downloader.download_v2.Path.glob', return_value=iter(['1.targets.json'])):
            downloader = TUFPointerDownloader(repository_url=_REPO_URL)
            downloader.download(_PROJECT, dest_dir=tmp_path)

        # Updater should have been asked for the 2.0.0 target, not 3.0.0rc1
        call_args = mock_updater.get_targetinfo.call_args[0][0]
        assert call_args == f'{_PROJECT}/2.0.0.json'


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


@pytest.mark.offline
class TestTargetNotFound:
    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.Metadata')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_raises_when_tuf_target_absent(self, mock_urlopen, mock_metadata_cls, mock_updater_cls, tmp_path):
        targets = _make_targets(_VERSION)
        mock_updater = MagicMock()
        mock_updater.get_targetinfo.return_value = None
        mock_updater_cls.return_value = mock_updater
        mock_metadata_cls.__getitem__.return_value.from_file.return_value.signed = targets

        with patch('datadog_checks.downloader.download_v2.Path.glob', return_value=iter(['1.targets.json'])):
            downloader = TUFPointerDownloader(repository_url=_REPO_URL)
            with pytest.raises(TargetNotFoundError, match=_PROJECT):
                downloader.get_pointer(_PROJECT, version='99.99.99')


@pytest.mark.offline
class TestDigestMismatch:
    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.Metadata')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_raises_on_corrupted_wheel(self, mock_urlopen, mock_metadata_cls, mock_updater_cls, tmp_path):
        targets = _make_targets(_VERSION)
        mock_updater_cls.return_value = _mock_tuf_updater(_POINTER)
        mock_metadata_cls.__getitem__.return_value.from_file.return_value.signed = targets

        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value.read.return_value = b'tampered bytes'

        with patch('datadog_checks.downloader.download_v2.Path.glob', return_value=iter(['1.targets.json'])):
            downloader = TUFPointerDownloader(repository_url=_REPO_URL)
            with pytest.raises(DigestMismatch, match=_PROJECT):
                downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)

    @patch('datadog_checks.downloader.download_v2.Updater')
    @patch('datadog_checks.downloader.download_v2.Metadata')
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_raises_on_length_mismatch(self, mock_urlopen, mock_metadata_cls, mock_updater_cls, tmp_path):
        targets = _make_targets(_VERSION)
        bad_pointer = {**_POINTER, 'length': _WHEEL_LENGTH + 1}
        mock_updater_cls.return_value = _mock_tuf_updater(bad_pointer)
        mock_metadata_cls.__getitem__.return_value.from_file.return_value.signed = targets

        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value.read.return_value = _WHEEL_CONTENT

        with patch('datadog_checks.downloader.download_v2.Path.glob', return_value=iter(['1.targets.json'])):
            downloader = TUFPointerDownloader(repository_url=_REPO_URL)
            with pytest.raises(DigestMismatch, match='length'):
                downloader.download(_PROJECT, version=_VERSION, dest_dir=tmp_path)


# ---------------------------------------------------------------------------
# Disable-verification mode
# ---------------------------------------------------------------------------


@pytest.mark.offline
class TestDisableVerification:
    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_skips_tuf_and_digest(self, mock_urlopen, tmp_path):
        """disable_verification fetches metadata chain to find hash-prefixed path,
        then downloads without digest checks."""
        from tuf.api.metadata import MetaFile, TargetFile

        # Build fake metadata responses
        ts = MagicMock()
        ts.snapshot_meta.version = 1
        ts_md = MagicMock()
        ts_md.signed = ts

        snap = MagicMock()
        snap.meta = {'targets.json': MagicMock(version=1)}
        snap_md = MagicMock()
        snap_md.signed = snap

        from tuf.api.metadata import TargetFile as TF
        tf = MagicMock()
        tf.hashes = {'sha256': 'a' * 64}
        targets = Targets()
        targets.targets[f'{_PROJECT}/{_VERSION}.json'] = tf
        tgt_md = MagicMock()
        tgt_md.signed = targets

        responses = [ts_md, snap_md, tgt_md]
        call_idx = [0]

        def fake_from_bytes(data):
            r = responses[call_idx[0]]
            call_idx[0] += 1
            return r

        pointer_bytes = json.dumps(_POINTER).encode()
        bad_pointer_bytes = json.dumps({**_POINTER, 'digest': 'deadbeef' * 8}).encode()

        url_call = [0]

        def fake_urlopen(url):
            url_call[0] += 1
            mock_resp = MagicMock()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            # First 3 calls: metadata; last: pointer file
            mock_resp.read.return_value = bad_pointer_bytes if url_call[0] > 3 else b'{}'
            return mock_resp

        mock_urlopen.side_effect = fake_urlopen

        with patch('datadog_checks.downloader.download_v2.Metadata') as mock_md:
            mock_md.__getitem__.return_value.from_bytes.side_effect = fake_from_bytes
            downloader = TUFPointerDownloader(repository_url=_REPO_URL, disable_verification=True)
            # Should not raise even though digest is wrong
            downloader.get_pointer(_PROJECT, version=_VERSION)

    @patch('datadog_checks.downloader.download_v2.urllib.request.urlopen')
    def test_404_raises_target_not_found(self, mock_urlopen):
        from tuf.api.metadata import TargetFile

        ts = MagicMock()
        ts.snapshot_meta.version = 1
        ts_md = MagicMock()
        ts_md.signed = ts

        snap = MagicMock()
        snap.meta = {'targets.json': MagicMock(version=1)}
        snap_md = MagicMock()
        snap_md.signed = snap

        tf = MagicMock()
        tf.hashes = {'sha256': 'a' * 64}
        targets = Targets()
        targets.targets[f'{_PROJECT}/{_VERSION}.json'] = tf
        tgt_md = MagicMock()
        tgt_md.signed = targets

        responses = [ts_md, snap_md, tgt_md]
        call_idx = [0]

        def fake_from_bytes(data):
            r = responses[call_idx[0]]
            call_idx[0] += 1
            return r

        http_404 = urllib.error.HTTPError('https://example.com', 404, 'Not Found', MagicMock(), None)

        url_call = [0]

        def fake_urlopen(url):
            url_call[0] += 1
            if url_call[0] > 3:
                raise http_404
            mock_resp = MagicMock()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.read.return_value = b'{}'
            return mock_resp

        mock_urlopen.side_effect = fake_urlopen

        with patch('datadog_checks.downloader.download_v2.Metadata') as mock_md:
            mock_md.__getitem__.return_value.from_bytes.side_effect = fake_from_bytes
            downloader = TUFPointerDownloader(repository_url=_REPO_URL, disable_verification=True)
            with pytest.raises(TargetNotFoundError):
                downloader.get_pointer(_PROJECT, version=_VERSION)
