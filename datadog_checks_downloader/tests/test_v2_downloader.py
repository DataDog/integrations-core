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

from datadog_checks.downloader import cli
from datadog_checks.downloader.download_v2 import TUFPointerDownloader
from datadog_checks.downloader.exceptions import (
    DigestMismatch,
    LengthMismatch,
    MalformedPointerError,
    MissingVersion,
    NonCanonicalVersion,
    NonDatadogPackage,
    TargetNotFoundError,
)

pytestmark = pytest.mark.offline

PROJECT = 'datadog-postgres'
VERSION = '14.0.0'
WHEEL_CONTENT = b'fake wheel bytes for testing'
WHEEL_DIGEST = hashlib.sha256(WHEEL_CONTENT).hexdigest()
WHEEL_LENGTH = len(WHEEL_CONTENT)
REPO_URL = 'https://agent-integration-wheels-staging.s3.amazonaws.com'

POINTER = {
    'digest': WHEEL_DIGEST,
    'length': WHEEL_LENGTH,
    'version': VERSION,
    'repository': REPO_URL,
    'wheel_path': f'/wheels/{PROJECT}/datadog_postgres-{VERSION}-py3-none-any.whl',
    'attestation_path': f'/attestations/{PROJECT}/{VERSION}.sigstore.json',
}


def _mock_tuf_updater(pointer: dict) -> MagicMock:
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
            pytest.param(VERSION, f'{PROJECT}/{VERSION}.json', id='explicit-version'),
            pytest.param(None, f'{PROJECT}/latest.json', id='missing-version'),
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
        assert wheel_path.name == f'datadog_postgres-{VERSION}-py3-none-any.whl'

    def test_repository_flag_overrides_pointer_repository(self, mock_urlopen, mock_updater_cls, tmp_path):
        prod_pointer = {**POINTER, 'repository': 'https://agent-integration-wheels-prod.s3.amazonaws.com'}
        mock_updater_cls.return_value = _mock_tuf_updater(prod_pointer)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)

        mock_urlopen.assert_called_once_with(
            f'{REPO_URL}/wheels/{PROJECT}/datadog_postgres-{VERSION}-py3-none-any.whl',
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


class TestLengthMismatch:
    def test_raises_when_pointer_length_does_not_match_wheel(self, mock_urlopen, mock_updater_cls, tmp_path):
        bad_pointer = {**POINTER, 'length': WHEEL_LENGTH + 1}
        mock_updater_cls.return_value = _mock_tuf_updater(bad_pointer)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(LengthMismatch) as exc_info:
            downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)
        assert exc_info.value.expected == WHEEL_LENGTH + 1
        assert exc_info.value.actual == WHEEL_LENGTH


class TestMalformedPointer:
    @pytest.mark.parametrize('missing_key', ['digest', 'length', 'wheel_path'])
    def test_raises_when_required_key_missing(self, mock_urlopen, mock_updater_cls, tmp_path, missing_key):
        broken_pointer = {k: v for k, v in POINTER.items() if k != missing_key}
        mock_updater_cls.return_value = _mock_tuf_updater(broken_pointer)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(MalformedPointerError, match=missing_key):
            downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)

    def test_raises_when_wheel_path_missing_leading_slash(self, mock_urlopen, mock_updater_cls, tmp_path):
        no_slash_pointer = {**POINTER, 'wheel_path': f'wheels/{PROJECT}/datadog_postgres-{VERSION}-py3-none-any.whl'}
        mock_updater_cls.return_value = _mock_tuf_updater(no_slash_pointer)

        downloader = TUFPointerDownloader(repository_url=REPO_URL)
        with pytest.raises(MalformedPointerError, match='wheel_path'):
            downloader.download(PROJECT, version=VERSION, dest_dir=tmp_path)
        mock_urlopen.assert_not_called()


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
            f'{REPO_URL}/wheels/{PROJECT}/datadog_postgres-{VERSION}-py3-none-any.whl',
            timeout=60,
        )
        assert wheel_path.name == f'datadog_postgres-{VERSION}-py3-none-any.whl'
        assert wheel_path.read_bytes() == content
        mock_updater_cls.assert_not_called()

    def test_direct_download_requires_explicit_version(self, tmp_path):
        downloader = TUFPointerDownloader(repository_url=REPO_URL, disable_verification=True)
        with pytest.raises(MissingVersion, match='requires an explicit --version'):
            downloader.download(PROJECT, dest_dir=tmp_path)


class TestInstantiateV2Downloader:
    def test_rejects_non_datadog_package(self, monkeypatch):
        monkeypatch.setattr('sys.argv', ['downloader', 'requests'])
        with pytest.raises(NonDatadogPackage, match='requests'):
            cli.instantiate_v2_downloader()

    def test_rejects_non_canonical_version(self, monkeypatch):
        monkeypatch.setattr('sys.argv', ['downloader', 'datadog-postgres', '--version', 'banana'])
        with pytest.raises(NonCanonicalVersion, match='banana'):
            cli.instantiate_v2_downloader()

    def test_warns_when_type_flag_supplied(self, monkeypatch, capsys):
        monkeypatch.setattr('sys.argv', ['downloader', 'datadog-postgres', '--type', 'core'])
        cli.instantiate_v2_downloader()
        assert 'WARNING: --type' in capsys.readouterr().err

    def test_warns_when_ignore_python_version_supplied(self, monkeypatch, capsys):
        monkeypatch.setattr('sys.argv', ['downloader', 'datadog-postgres', '--ignore-python-version'])
        cli.instantiate_v2_downloader()
        assert 'NOTE: --ignore-python-version' in capsys.readouterr().err

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

    def test_default_falls_back_to_v1_on_v2_download_failure(self, monkeypatch):
        monkeypatch.setattr('sys.argv', ['downloader', 'datadog-postgres'])
        monkeypatch.setattr(cli, 'run_v2_downloader', MagicMock(side_effect=TargetNotFoundError('missing')))
        v1 = MagicMock()
        monkeypatch.setattr(cli, 'run_downloader', v1)
        monkeypatch.setattr(cli, 'instantiate_downloader', MagicMock(return_value=('d', 'n', 'v', False)))

        cli.download()
        v1.assert_called_once_with('d', 'n', 'v', False)

    def test_non_datadog_package_does_not_fall_back_to_v1(self, monkeypatch):
        monkeypatch.setattr('sys.argv', ['downloader', 'requests'])
        v1 = MagicMock()
        monkeypatch.setattr(cli, 'run_downloader', v1)
        monkeypatch.setattr(cli, 'instantiate_downloader', MagicMock())

        with pytest.raises(NonDatadogPackage):
            cli.download()
        v1.assert_not_called()
