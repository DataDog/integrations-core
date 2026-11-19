# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections import namedtuple
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ddev.release.placeholders import (
    PYPI_UPLOAD_URL,
    TOKEN_ENV_VAR,
    build_placeholder,
    get_api_token,
    mint_oidc_token,
    needs_placeholder,
    oidc_publishing_available,
    placeholder_package_names,
    resolve_placeholder_name,
    upload_placeholder,
)

FakeIntegration = namedtuple('FakeIntegration', ['name', 'path'])


def _make_integration(tmp_path: Path, name: str, package_name: str | None) -> FakeIntegration:
    path = tmp_path / name
    path.mkdir()
    if package_name is not None:
        (path / 'pyproject.toml').write_text(f'[project]\nname = "{package_name}"\n')
    return FakeIntegration(name, path)


def _make_repo(integrations):
    repo = MagicMock()
    repo.integrations.iter_packages.return_value = iter(integrations)
    return repo


class TestPlaceholderPackageNames:
    def test_maps_integration_names_to_package_names_and_excludes_real_packages(self, tmp_path):
        repo = _make_repo(
            [
                _make_integration(tmp_path, 'n8n', 'datadog-n8n'),
                _make_integration(tmp_path, 'kafka_consumer', 'datadog-kafka-consumer'),
                _make_integration(tmp_path, 'ddev', 'ddev'),
                _make_integration(tmp_path, 'datadog_checks_base', 'datadog-checks-base'),
                _make_integration(tmp_path, 'tile_only', None),
            ]
        )

        assert placeholder_package_names(repo) == {
            'n8n': 'datadog-n8n',
            'kafka_consumer': 'datadog-kafka-consumer',
        }


class TestResolvePlaceholderName:
    def test_accepts_integration_package_and_retired_names(self):
        package_names = {'n8n': 'datadog-n8n', 'kafka_consumer': 'datadog-kafka-consumer'}

        assert resolve_placeholder_name('n8n', package_names) == 'datadog-n8n'
        assert resolve_placeholder_name('datadog-n8n', package_names) == 'datadog-n8n'
        assert resolve_placeholder_name('kafka-consumer', package_names) == 'datadog-kafka-consumer'
        assert resolve_placeholder_name('datadog-tokumx', package_names) == 'datadog-tokumx'
        assert resolve_placeholder_name('whatever', package_names) is None

    @pytest.mark.parametrize(
        ('requested', 'expected'),
        [
            ('kafka_consumer', 'datadog-kafka-consumer'),
            ('datadog-kafka_consumer', 'datadog-kafka-consumer'),
            ('Datadog-N8N', 'datadog-n8n'),
            ('datadog_tokumx', 'datadog-tokumx'),
        ],
    )
    def test_matches_names_the_way_pypi_normalizes_them(self, requested, expected):
        package_names = {'n8n': 'datadog-n8n', 'kafka_consumer': 'datadog-kafka-consumer'}

        assert resolve_placeholder_name(requested, package_names) == expected


class TestNeedsPlaceholder:
    def test_missing_package_needs_placeholder(self, mocker):
        response = mocker.Mock(status_code=404)
        mocker.patch('ddev.release.placeholders.httpx.get', return_value=response)

        assert needs_placeholder('datadog-n8n')

    @pytest.mark.parametrize(('version', 'expected'), [('0.0.1', True), ('0.0.2', False), ('2.3.0', False)])
    def test_version_decides(self, mocker, version, expected):
        response = mocker.Mock(status_code=200)
        response.json.return_value = {'info': {'version': version}}
        mocker.patch('ddev.release.placeholders.httpx.get', return_value=response)

        assert needs_placeholder('datadog-n8n') is expected


class TestGetApiToken:
    def test_reads_environment(self, mocker, monkeypatch):
        monkeypatch.setenv(TOKEN_ENV_VAR, 'pypi-xxx')
        mocker.patch('ddev.release.placeholders.getpass.getpass')

        assert get_api_token() == 'pypi-xxx'

    def test_prompts_in_a_terminal(self, mocker, monkeypatch):
        monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)
        mocker.patch('ddev.release.placeholders.sys.stdin.isatty', return_value=True)
        mocker.patch('ddev.release.placeholders.sys.stdout.isatty', return_value=True)
        mocker.patch('ddev.release.placeholders.getpass.getpass', return_value='pypi-yyy')

        assert get_api_token() == 'pypi-yyy'

    def test_returns_none_without_terminal_or_environment(self, mocker, monkeypatch):
        monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)
        mocker.patch('ddev.release.placeholders.sys.stdin.isatty', return_value=False)
        mocker.patch('ddev.release.placeholders.getpass.getpass')

        assert get_api_token() is None


class TestOidcPublishing:
    def test_available_only_with_github_actions_oidc(self, monkeypatch):
        monkeypatch.delenv('ACTIONS_ID_TOKEN_REQUEST_URL', raising=False)
        monkeypatch.delenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', raising=False)
        assert not oidc_publishing_available()

        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_URL', 'https://github/token')
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', 'secret')
        assert oidc_publishing_available()

    def test_mints_token_per_exchange(self, mocker, monkeypatch):
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_URL', 'https://github/token?api-version=1')
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', 'secret')
        github_response = mocker.Mock()
        github_response.json.return_value = {'value': 'oidc-jwt'}
        mint_response = mocker.Mock(status_code=200)
        mint_response.json.return_value = {'token': 'pypi-minted'}
        httpx_get = mocker.patch('ddev.release.placeholders.httpx.get', return_value=github_response)
        httpx_post = mocker.patch('ddev.release.placeholders.httpx.post', return_value=mint_response)

        assert mint_oidc_token() == 'pypi-minted'
        assert httpx_get.call_args.kwargs['headers']['Authorization'] == 'bearer secret'
        assert httpx_get.call_args.kwargs['params'] == {'audience': 'pypi'}
        assert httpx_post.call_args.kwargs['json'] == {'token': 'oidc-jwt'}

    def test_mint_failure_raises_the_pypi_error(self, mocker, monkeypatch):
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_URL', 'https://github/token?api-version=1')
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', 'secret')
        github_response = mocker.Mock()
        github_response.json.return_value = {'value': 'oidc-jwt'}
        mint_response = mocker.Mock(status_code=400)
        mint_response.text = 'invalid-publisher'
        mocker.patch('ddev.release.placeholders.httpx.get', return_value=github_response)
        mocker.patch('ddev.release.placeholders.httpx.post', return_value=mint_response)

        with pytest.raises(RuntimeError, match='invalid-publisher'):
            mint_oidc_token()


class TestBuildPlaceholder:
    def test_wheel_carries_the_pointer_module_and_readme(self, tmp_path):
        import zipfile

        wheel = build_placeholder('datadog-n8n', tmp_path)

        assert wheel.name == 'datadog_n8n-0.0.2-py2.py3-none-any.whl'
        with zipfile.ZipFile(wheel) as archive:
            names = set(archive.namelist())
            metadata = archive.read('datadog_n8n-0.0.2.dist-info/METADATA').decode()
        assert 'datadog_n8n/__init__.py' in names
        assert 'https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install' in metadata

    def test_build_failure_carries_the_hatchling_output(self, tmp_path, mocker):
        import subprocess

        error = subprocess.CalledProcessError(1, ['hatchling', 'build'], stderr=b'invalid metadata')
        mocker.patch('ddev.release.placeholders.subprocess.run', side_effect=error)

        with pytest.raises(RuntimeError, match='invalid metadata'):
            build_placeholder('datadog-n8n', tmp_path)


class TestUploadPlaceholder:
    def test_uploads_with_token_auth_and_skip_existing(self, mocker):
        uploaded = mocker.patch('ddev.release.placeholders.upload')

        upload_placeholder(Path('dist/x.whl'), 'pypi-xxx')

        settings, dists = uploaded.call_args.args
        assert Path(dists[0]) == Path('dist/x.whl')
        assert settings.repository_config['repository'] == PYPI_UPLOAD_URL
        assert settings.username == '__token__'
        assert settings.password == 'pypi-xxx'
        assert settings.skip_existing is True


class TestPlaceholdersCommand:
    def test_dry_run_lists_the_selected_names(self, ddev, mocker):
        mocker.patch('ddev.release.placeholders.needs_placeholder', return_value=True)

        result = ddev('release', 'placeholders', 'n8n', '--dry-run')

        assert result.exit_code == 0, result.output
        assert 'datadog-n8n' in result.output

    def test_skips_names_that_already_have_a_release(self, ddev, mocker):
        mocker.patch('ddev.release.placeholders.needs_placeholder', return_value=False)

        result = ddev('release', 'placeholders', 'n8n', '--dry-run')

        assert result.exit_code == 0, result.output
        assert 'skip datadog-n8n (already published)' in result.output
        assert 'Nothing to publish.' in result.output

    def test_unknown_name_aborts(self, ddev):
        result = ddev('release', 'placeholders', 'not-an-integration', '--dry-run')

        assert result.exit_code == 1
        assert 'Unknown integration or package name: not-an-integration' in result.output
