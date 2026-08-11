# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Unit tests for TUFPointerDownloader (v2 repository format) and the v2 CLI surface."""

import hashlib
import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from tuf.api.exceptions import DownloadError

from datadog_checks.downloader import cli
from datadog_checks.downloader.download_v2 import (
    V2_POINTER_TARGET_DELEGATION,
    V2_POINTER_TARGET_PREFIX,
    TUFPointerDownloader,
)
from datadog_checks.downloader.exceptions import (
    DigestMismatch,
    LengthMismatch,
    MalformedPointerError,
    MissingVersion,
    NonCanonicalVersion,
    NonDatadogPackage,
    TargetNotFoundError,
)

from ._v2_synth_repo import build_delegated_repo, serve_directory

pytestmark = pytest.mark.offline

PROJECT = 'datadog-postgres'
VERSION = '14.0.0'
WHEEL_NAME = f'datadog_postgres-{VERSION}-py3-none-any.whl'
WHEEL_CONTENT = b'fake wheel bytes for testing'
WHEEL_DIGEST = hashlib.sha256(WHEEL_CONTENT).hexdigest()
WHEEL_LENGTH = len(WHEEL_CONTENT)
REPO_URL = 'https://agent-integration-wheels.datadoghq.com'

POINTER = {
    'digest': WHEEL_DIGEST,
    'length': WHEEL_LENGTH,
    'version': VERSION,
    'repository': REPO_URL,
    'wheel_path': f'/wheels/{PROJECT}/{WHEEL_NAME}',
    'attestation_path': f'/attestations/{PROJECT}/{VERSION}.sigstore.json',
}


def _mock_tuf_updater(pointer: dict) -> MagicMock:
    return _mock_tuf_updater_with_pointer_bytes(json.dumps(pointer).encode())


def _mock_tuf_updater_with_pointer_bytes(pointer_bytes: bytes) -> MagicMock:
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
        mock.return_value = _mock_response(WHEEL_CONTENT)
        yield mock


@pytest.fixture
def mock_updater_cls():
    with patch('datadog_checks.downloader.download_v2.Updater') as mock:
        mock.return_value = _mock_tuf_updater(POINTER)
        yield mock


class TestTargetResolution:
    @pytest.mark.parametrize(
        'version,expected_target',
        [
            pytest.param(VERSION, f'wheelsmith/v1/{PROJECT}/{VERSION}.json', id='explicit-version'),
            pytest.param(None, f'wheelsmith/v1/{PROJECT}/latest.json', id='missing-version'),
        ],
    )
    def test_get_pointer_requests_expected_target(self, mock_urlopen, mock_updater_cls, version, expected_target):
        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        downloader.get_pointer(PROJECT, version=version)

        mock_updater = mock_updater_cls.return_value
        assert mock_updater.get_targetinfo.call_args[0][0] == expected_target


class TestHappyPath:
    def test_download_returns_wheel_path(self, mock_urlopen, mock_updater_cls, tmp_path):
        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        wheel_path = downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)

        assert wheel_path.exists()
        assert wheel_path.read_bytes() == WHEEL_CONTENT
        assert wheel_path.name == WHEEL_NAME

    def test_repository_flag_overrides_pointer_repository(self, mock_urlopen, mock_updater_cls, tmp_path):
        prod_pointer = {**POINTER, 'repository': 'https://agent-integration-wheels-prod.s3.amazonaws.com'}
        mock_updater_cls.return_value = _mock_tuf_updater(prod_pointer)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)

        mock_urlopen.assert_called_once_with(
            f'{REPO_URL}/wheels/{PROJECT}/{WHEEL_NAME}',
            timeout=60,
        )


class TestTargetNotFound:
    def test_raises_when_tuf_target_absent(self, mock_urlopen, mock_updater_cls):
        mock_updater = MagicMock()
        mock_updater.get_targetinfo.return_value = None
        mock_updater_cls.return_value = mock_updater

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(TargetNotFoundError, match=PROJECT):
            downloader.get_pointer(PROJECT, version='99.99.99')


class TestDigestMismatch:
    def test_raises_on_corrupted_wheel(self, mock_urlopen, mock_updater_cls, tmp_path):
        tampered = b'tampered bytes that match the pointer length'[:WHEEL_LENGTH]
        mock_urlopen.return_value = _mock_response(tampered)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(DigestMismatch, match=PROJECT):
            downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)
        assert not (tmp_path / WHEEL_NAME).exists()


class TestLengthMismatch:
    def test_raises_when_pointer_length_does_not_match_wheel(self, mock_urlopen, mock_updater_cls, tmp_path):
        bad_pointer = {**POINTER, 'length': WHEEL_LENGTH + 1}
        mock_updater_cls.return_value = _mock_tuf_updater(bad_pointer)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(LengthMismatch) as exc_info:
            downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)
        assert exc_info.value.expected == WHEEL_LENGTH + 1
        assert exc_info.value.actual == WHEEL_LENGTH
        assert not (tmp_path / WHEEL_NAME).exists()


class TestMalformedPointer:
    @pytest.mark.parametrize('missing_key', ['digest', 'length', 'wheel_path'])
    def test_raises_when_required_key_missing(self, mock_urlopen, mock_updater_cls, tmp_path, missing_key):
        broken_pointer = {k: v for k, v in POINTER.items() if k != missing_key}
        mock_updater_cls.return_value = _mock_tuf_updater(broken_pointer)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(MalformedPointerError, match=missing_key):
            downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)

    def test_raises_when_wheel_path_missing_leading_slash(self, mock_urlopen, mock_updater_cls, tmp_path):
        no_slash_pointer = {**POINTER, 'wheel_path': f'wheels/{PROJECT}/{WHEEL_NAME}'}
        mock_updater_cls.return_value = _mock_tuf_updater(no_slash_pointer)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(MalformedPointerError, match='wheel_path'):
            downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)
        mock_urlopen.assert_not_called()

    @pytest.mark.parametrize(
        'pointer_bytes',
        [
            pytest.param(b'["digest", "length", "wheel_path"]', id='list'),
            pytest.param(b'"not an object"', id='string'),
        ],
    )
    def test_raises_when_pointer_payload_is_not_object(self, mock_urlopen, mock_updater_cls, tmp_path, pointer_bytes):
        mock_updater_cls.return_value = _mock_tuf_updater_with_pointer_bytes(pointer_bytes)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(MalformedPointerError, match='pointer'):
            downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)
        mock_urlopen.assert_not_called()

    @pytest.mark.parametrize(
        'wheel_path',
        [
            pytest.param(f'//evil.example.com/wheels/{PROJECT}/{WHEEL_NAME}', id='scheme-bypass-double-slash'),
            pytest.param(f'/wheels/../{PROJECT}/{WHEEL_NAME}', id='parent-dir-segment'),
            pytest.param(f'/wheels/{PROJECT}/../{WHEEL_NAME}', id='parent-dir-segment-trailing'),
            pytest.param(f'/wheels//{PROJECT}/{WHEEL_NAME}', id='empty-segment'),
        ],
    )
    def test_rejects_path_traversal_or_scheme_bypass_in_wheel_path(
        self, mock_urlopen, mock_updater_cls, tmp_path, wheel_path
    ):
        bad_pointer = {**POINTER, 'wheel_path': wheel_path}
        mock_updater_cls.return_value = _mock_tuf_updater(bad_pointer)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(MalformedPointerError, match='wheel_path'):
            downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)
        mock_urlopen.assert_not_called()

    @pytest.mark.parametrize(
        'pointer_digest',
        [
            pytest.param(123, id='non-string'),
            pytest.param('not-hex!' * 8, id='non-hex'),
            pytest.param('a' * 63, id='too-short'),
            pytest.param('a' * 65, id='too-long'),
            pytest.param(WHEEL_DIGEST.upper(), id='uppercase'),
        ],
    )
    def test_rejects_invalid_digest(self, mock_urlopen, mock_updater_cls, tmp_path, pointer_digest):
        bad_pointer = {**POINTER, 'digest': pointer_digest}
        mock_updater_cls.return_value = _mock_tuf_updater(bad_pointer)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(MalformedPointerError, match='digest'):
            downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)
        mock_urlopen.assert_not_called()

    @pytest.mark.parametrize(
        'pointer_length',
        [
            pytest.param('27', id='string'),
            pytest.param(-1, id='negative'),
            pytest.param(True, id='bool-true'),
            pytest.param(None, id='none'),
        ],
    )
    def test_rejects_invalid_length(self, mock_urlopen, mock_updater_cls, tmp_path, pointer_length):
        bad_pointer = {**POINTER, 'length': pointer_length}
        mock_updater_cls.return_value = _mock_tuf_updater(bad_pointer)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(MalformedPointerError, match='length'):
            downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)
        mock_urlopen.assert_not_called()

    def test_extra_unknown_keys_are_forward_compatible(self, mock_urlopen, mock_updater_cls, tmp_path):
        forward_compat = {**POINTER, 'future_feature': {'enabled': True}, 'signing_metadata_url': '/x'}
        mock_updater_cls.return_value = _mock_tuf_updater(forward_compat)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        wheel_path = downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)
        assert wheel_path.read_bytes() == WHEEL_CONTENT

    def test_zero_length_wheel_is_allowed(self, mock_urlopen, mock_updater_cls, tmp_path):
        empty_digest = hashlib.sha256(b'').hexdigest()
        empty_pointer = {**POINTER, 'digest': empty_digest, 'length': 0}
        mock_updater_cls.return_value = _mock_tuf_updater(empty_pointer)
        mock_urlopen.return_value = _mock_response(b'')

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        wheel_path = downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)
        assert wheel_path.read_bytes() == b''


class TestNetworkErrorMidDownload:
    def test_http_error_propagates(self, mock_urlopen, mock_updater_cls, tmp_path):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='http://example/x.whl', code=500, msg='boom', hdrs=None, fp=None
        )

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(urllib.error.HTTPError):
            downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)

    def test_url_error_propagates(self, mock_urlopen, mock_updater_cls, tmp_path):
        mock_urlopen.side_effect = urllib.error.URLError('unreachable')

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(urllib.error.URLError):
            downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)


class TestDisableVerification:
    def test_directly_downloads_wheel_without_tuf_or_digest_checks(self, mock_urlopen, mock_updater_cls, tmp_path):
        content = b'bytes not matching any signed pointer'
        mock_urlopen.return_value = _mock_response(content)

        downloader = TUFPointerDownloader(repository_url=REPO_URL, disable_verification=True)
        wheel_path = downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)

        mock_urlopen.assert_called_once_with(
            f'{REPO_URL}/wheels/{PROJECT}/{WHEEL_NAME}',
            timeout=60,
        )
        assert wheel_path.name == WHEEL_NAME
        assert wheel_path.read_bytes() == content
        mock_updater_cls.assert_not_called()

    def test_direct_download_requires_explicit_version(self, tmp_path):
        downloader = TUFPointerDownloader(repository_url=REPO_URL, disable_verification=True)
        with pytest.raises(MissingVersion, match='requires an explicit --version'):
            downloader.download(PROJECT, dest_dir=tmp_path)


class TestUpdaterContract:
    """Lock in the v2 target-path storage contract."""

    def test_get_targetinfo_called_with_prefixed_path_only(self, mock_urlopen, mock_updater_cls):
        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        downloader.get_pointer(PROJECT, version=VERSION)

        mock_updater = mock_updater_cls.return_value
        call = mock_updater.get_targetinfo.call_args
        assert call.args == (f'wheelsmith/v1/{PROJECT}/{VERSION}.json',)
        assert call.kwargs == {}

    def test_target_path_uses_stable_wheelsmith_namespace(self, mock_urlopen, mock_updater_cls):
        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        downloader.get_pointer(PROJECT, version=VERSION)

        target_path = mock_updater_cls.return_value.get_targetinfo.call_args.args[0]
        assert target_path.startswith('wheelsmith/v1/')
        assert not target_path.startswith('targets/')
        assert not target_path.startswith('wheels-signer-')


def _patch_bootstrap_to_use(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make TUFPointerDownloader trust the synthetic repo's root.json instead of the bundled one."""

    def fake_bootstrap(self, metadata_dir: Path) -> None:
        (metadata_dir / 'root.json').write_bytes((repo_root / 'metadata' / 'root.json').read_bytes())

    monkeypatch.setattr(TUFPointerDownloader, '_bootstrap_metadata_dir', fake_bootstrap)


class TestDelegationTraversal:
    """Test v2 target resolution through delegated TUF metadata."""

    @staticmethod
    def _make_pointer_target(project: str, version: str) -> tuple[str, bytes, dict]:
        wheel = b'synthetic wheel for delegation test'
        wheel_name = f'{project.replace("-", "_")}-{version}-py3-none-any.whl'
        pointer = {
            'digest': hashlib.sha256(wheel).hexdigest(),
            'length': len(wheel),
            'version': version,
            'repository': REPO_URL,
            'wheel_path': f'/wheels/{project}/{wheel_name}',
        }
        return wheel_name, wheel, pointer

    def test_resolves_through_paths_delegation_without_naming_role(self, monkeypatch, tmp_path):
        project, version = 'datadog-postgres', '14.0.0'
        _, _, pointer = self._make_pointer_target(project, version)

        repo = tmp_path / 'repo'
        build_delegated_repo(
            repo,
            delegated_targets={f'{V2_POINTER_TARGET_PREFIX}/{project}/{version}.json': json.dumps(pointer).encode()},
            delegated_role_name=V2_POINTER_TARGET_DELEGATION,
            paths=[f'{V2_POINTER_TARGET_PREFIX}/{project}/*'],
        )
        _patch_bootstrap_to_use(repo, monkeypatch)

        with serve_directory(repo) as url:
            downloader = TUFPointerDownloader(repository_url=url)
            assert downloader.get_pointer(project, version=version) == pointer

    def test_resolves_through_hash_prefix_delegation(self, monkeypatch, tmp_path):
        project, version = 'datadog-postgres', '14.0.0'
        target_path = f'{V2_POINTER_TARGET_PREFIX}/{project}/{version}.json'
        _, _, pointer = self._make_pointer_target(project, version)

        prefix = hashlib.sha256(target_path.encode()).hexdigest()[:2]

        repo = tmp_path / 'repo'
        build_delegated_repo(
            repo,
            delegated_targets={target_path: json.dumps(pointer).encode()},
            delegated_role_name=V2_POINTER_TARGET_DELEGATION,
            path_hash_prefixes=[prefix],
        )
        _patch_bootstrap_to_use(repo, monkeypatch)

        with serve_directory(repo) as url:
            downloader = TUFPointerDownloader(repository_url=url)
            assert downloader.get_pointer(project, version=version) == pointer

    def test_unmatched_target_path_raises_not_found(self, monkeypatch, tmp_path):
        project, version = 'datadog-postgres', '14.0.0'
        _, _, pointer = self._make_pointer_target(project, version)

        repo = tmp_path / 'repo'
        build_delegated_repo(
            repo,
            delegated_targets={f'{V2_POINTER_TARGET_PREFIX}/{project}/{version}.json': json.dumps(pointer).encode()},
            delegated_role_name=V2_POINTER_TARGET_DELEGATION,
            paths=[f'{V2_POINTER_TARGET_PREFIX}/datadog-postgres/*'],
        )
        _patch_bootstrap_to_use(repo, monkeypatch)

        with serve_directory(repo) as url:
            downloader = TUFPointerDownloader(repository_url=url)
            with pytest.raises(TargetNotFoundError, match='datadog-redis'):
                downloader.get_pointer('datadog-redis', version=version)


class TestInstantiateV2Downloader:
    def test_rejects_non_datadog_package(self, monkeypatch):
        monkeypatch.setattr('sys.argv', ['downloader', 'requests'])
        with pytest.raises(NonDatadogPackage, match='requests'):
            cli.instantiate_v2_downloader()

    def test_rejects_non_canonical_version(self, monkeypatch):
        monkeypatch.setattr('sys.argv', ['downloader', 'datadog-postgres', '--version', 'banana'])
        with pytest.raises(NonCanonicalVersion, match='banana'):
            cli.instantiate_v2_downloader()

    def test_does_not_warn_when_v1_compat_flags_are_parsed(self, monkeypatch, capsys):
        monkeypatch.setattr('sys.argv', ['downloader', 'datadog-postgres', '--type', 'core', '--ignore-python-version'])
        cli.instantiate_v2_downloader()
        assert capsys.readouterr().err == ''

    def test_warns_for_v1_compat_flags_in_strict_v2_mode(self, monkeypatch, capsys):
        monkeypatch.setattr(
            'sys.argv', ['downloader', 'datadog-postgres', '--v2', '--type', 'core', '--ignore-python-version']
        )
        _, _, _, args = cli.instantiate_v2_downloader()
        cli.warn_v2_ignored_args(args)
        stderr = capsys.readouterr().err
        assert 'WARNING: --type' in stderr
        assert 'NOTE: --ignore-python-version' in stderr

    def test_force_flag_is_silently_ignored(self, monkeypatch, capsys):
        monkeypatch.setattr('sys.argv', ['downloader', 'datadog-postgres', '--force'])
        cli.instantiate_v2_downloader()
        assert capsys.readouterr().err == ''


class TestCliDownloadFallback:
    """Covers the cli.download() v2-attempt-then-v1-fallback orchestration."""

    def test_strict_v2_raises_on_v2_failure(self, monkeypatch):
        monkeypatch.setattr('sys.argv', ['downloader', 'datadog-postgres', '--v2'])
        monkeypatch.setattr(cli, 'run_v2_downloader', MagicMock(side_effect=TargetNotFoundError('missing')))
        v1 = MagicMock()
        monkeypatch.setattr(cli, 'run_downloader', v1)
        monkeypatch.setattr(cli, 'instantiate_downloader', MagicMock(return_value=(None, None, None, None)))

        with pytest.raises(TargetNotFoundError):
            cli.download()
        v1.assert_not_called()

    @pytest.mark.parametrize(
        'fallback_exc',
        [
            pytest.param(MissingVersion('missing'), id='missing-version'),
            pytest.param(TargetNotFoundError('missing'), id='target-not-found'),
            pytest.param(DownloadError('unreachable'), id='download-error'),
            pytest.param(TimeoutError('slow'), id='timeout-error'),
            pytest.param(urllib.error.URLError('unreachable'), id='url-error'),
        ],
    )
    def test_default_falls_back_to_v1_on_expected_v2_failures(self, monkeypatch, fallback_exc):
        monkeypatch.setattr('sys.argv', ['downloader', 'datadog-postgres'])
        monkeypatch.setattr(cli, 'run_v2_downloader', MagicMock(side_effect=fallback_exc))
        v1 = MagicMock()
        monkeypatch.setattr(cli, 'run_downloader', v1)
        monkeypatch.setattr(cli, 'instantiate_downloader', MagicMock(return_value=('d', 'n', 'v', False)))

        cli.download()
        v1.assert_called_once_with('d', 'n', 'v', False)

    def test_default_unsafe_disable_verification_without_version_falls_back_to_v1(self, monkeypatch):
        monkeypatch.setattr('sys.argv', ['downloader', 'datadog-postgres', '--unsafe-disable-verification'])
        monkeypatch.setattr(cli, 'run_v2_downloader', MagicMock(side_effect=MissingVersion('missing')))
        v1 = MagicMock()
        monkeypatch.setattr(cli, 'run_downloader', v1)
        monkeypatch.setattr(cli, 'instantiate_downloader', MagicMock(return_value=('d', 'n', None, False)))

        cli.download()
        v1.assert_called_once_with('d', 'n', None, False)

    def test_non_datadog_package_does_not_fall_back_to_v1(self, monkeypatch):
        monkeypatch.setattr('sys.argv', ['downloader', 'requests'])
        v1 = MagicMock()
        monkeypatch.setattr(cli, 'run_downloader', v1)
        monkeypatch.setattr(cli, 'instantiate_downloader', MagicMock())

        with pytest.raises(NonDatadogPackage):
            cli.download()
        v1.assert_not_called()

    @pytest.mark.parametrize(
        'integrity_exc',
        [
            pytest.param(DigestMismatch(PROJECT, 'a', 'b'), id='digest-mismatch'),
            pytest.param(LengthMismatch(PROJECT, 1, 2), id='length-mismatch'),
            pytest.param(MalformedPointerError(PROJECT, 'digest'), id='malformed-pointer'),
        ],
    )
    def test_integrity_errors_do_not_fall_back_to_v1(self, monkeypatch, integrity_exc):
        monkeypatch.setattr('sys.argv', ['downloader', 'datadog-postgres'])
        monkeypatch.setattr(cli, 'run_v2_downloader', MagicMock(side_effect=integrity_exc))
        v1 = MagicMock()
        monkeypatch.setattr(cli, 'run_downloader', v1)
        monkeypatch.setattr(cli, 'instantiate_downloader', MagicMock())

        with pytest.raises(type(integrity_exc)):
            cli.download()
        v1.assert_not_called()
