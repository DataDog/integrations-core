# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections import namedtuple
from pathlib import Path
from unittest.mock import create_autospec

import httpx
import pytest

from ddev.release.placeholders import (
    build_placeholder,
    get_api_token,
    mint_oidc_token,
    needs_placeholder,
    placeholder_package_names,
    resolve_placeholder_name,
    upload_placeholder,
)
from ddev.repo.core import IntegrationRegistry, Repository

FakeIntegration = namedtuple('FakeIntegration', ['name', 'path'])


def _json_response(payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload, request=httpx.Request('GET', 'https://pypi.org'))


def _make_integration(tmp_path: Path, name: str, package_name: str | None) -> FakeIntegration:
    path = tmp_path / name
    path.mkdir()
    if package_name is not None:
        (path / 'pyproject.toml').write_text(f'[project]\nname = "{package_name}"\n')
    return FakeIntegration(name, path)


def _make_repo(integrations):
    repo = create_autospec(Repository, instance=True)
    registry = create_autospec(IntegrationRegistry, instance=True)
    registry.iter_packages.return_value = iter(integrations)
    repo.integrations = registry
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
        mocker.patch('ddev.release.placeholders.httpx.get', autospec=True, return_value=httpx.Response(404))

        assert needs_placeholder('datadog-n8n')

    @pytest.mark.parametrize(('version', 'expected'), [('0.0.1', True), ('0.0.2', False), ('2.3.0', False)])
    def test_version_decides(self, mocker, version, expected):
        response = _json_response({'info': {'version': version}})
        mocker.patch('ddev.release.placeholders.httpx.get', autospec=True, return_value=response)

        assert needs_placeholder('datadog-n8n') is expected


class TestGetApiToken:
    def test_reads_environment(self, mocker, monkeypatch):
        monkeypatch.setenv('DDEV_PYPI_TOKEN', 'pypi-xxx')
        mocker.patch('ddev.release.placeholders.getpass.getpass', autospec=True)

        assert get_api_token() == 'pypi-xxx'

    def test_prompts_in_a_terminal(self, mocker, monkeypatch):
        monkeypatch.delenv('DDEV_PYPI_TOKEN', raising=False)
        mocker.patch('ddev.release.placeholders.sys.stdin.isatty', autospec=True, return_value=True)
        mocker.patch('ddev.release.placeholders.sys.stdout.isatty', autospec=True, return_value=True)
        mocker.patch('ddev.release.placeholders.getpass.getpass', autospec=True, return_value='pypi-yyy')

        assert get_api_token() == 'pypi-yyy'

    def test_returns_none_without_terminal_or_environment(self, mocker, monkeypatch):
        monkeypatch.delenv('DDEV_PYPI_TOKEN', raising=False)
        mocker.patch('ddev.release.placeholders.sys.stdin.isatty', autospec=True, return_value=False)
        mocker.patch('ddev.release.placeholders.getpass.getpass', autospec=True)

        assert get_api_token() is None


class TestMintOidcToken:
    def test_mints_token_per_exchange(self, mocker, monkeypatch):
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_URL', 'https://github/token?api-version=1')
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', 'secret')
        httpx_get = mocker.patch(
            'ddev.release.placeholders.httpx.get', autospec=True, return_value=_json_response({'value': 'oidc-jwt'})
        )
        httpx_post = mocker.patch(
            'ddev.release.placeholders.httpx.post',
            autospec=True,
            return_value=httpx.Response(200, json={'token': 'pypi-minted'}),
        )

        assert mint_oidc_token() == 'pypi-minted'
        assert httpx_get.call_args.kwargs['headers']['Authorization'] == 'bearer secret'
        assert httpx_get.call_args.kwargs['params'] == {'audience': 'pypi'}
        assert httpx_post.call_args.kwargs['json'] == {'token': 'oidc-jwt'}

    def test_mint_failure_raises_the_pypi_error(self, mocker, monkeypatch):
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_URL', 'https://github/token?api-version=1')
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', 'secret')
        mocker.patch(
            'ddev.release.placeholders.httpx.get', autospec=True, return_value=_json_response({'value': 'oidc-jwt'})
        )
        mocker.patch(
            'ddev.release.placeholders.httpx.post',
            autospec=True,
            return_value=httpx.Response(400, text='invalid-publisher'),
        )

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
        mocker.patch('ddev.release.placeholders.subprocess.run', autospec=True, side_effect=error)

        with pytest.raises(RuntimeError, match='invalid metadata'):
            build_placeholder('datadog-n8n', tmp_path)


class TestUploadPlaceholder:
    def test_uploads_with_token_auth_and_skip_existing(self, mocker):
        uploaded = mocker.patch('ddev.release.placeholders.upload', autospec=True)

        upload_placeholder(Path('dist/x.whl'), 'pypi-xxx')

        settings, dists = uploaded.call_args.args
        assert Path(dists[0]) == Path('dist/x.whl')
        assert settings.repository_config['repository'] == 'https://upload.pypi.org/legacy/'
        assert settings.username == '__token__'
        assert settings.password == 'pypi-xxx'
        assert settings.skip_existing is True


class TestPlaceholdersCommand:
    def test_dry_run_lists_the_selected_names(self, ddev, mocker):
        mocker.patch('ddev.release.placeholders.needs_placeholder', autospec=True, return_value=True)

        result = ddev('release', 'placeholders', 'n8n', '--dry-run')

        assert result.exit_code == 0, result.output
        assert 'datadog-n8n' in result.output

    def test_skips_names_that_already_have_a_release(self, ddev, mocker):
        mocker.patch('ddev.release.placeholders.needs_placeholder', autospec=True, return_value=False)

        result = ddev('release', 'placeholders', 'n8n', '--dry-run')

        assert result.exit_code == 0, result.output
        assert 'skip datadog-n8n (already published)' in result.output
        assert 'Nothing to publish.' in result.output

    def test_unknown_name_aborts(self, ddev):
        result = ddev('release', 'placeholders', 'not-an-integration', '--dry-run')

        assert result.exit_code == 1
        assert 'Unknown integration or package name: not-an-integration' in result.output

    def test_aborts_without_a_token_or_trusted_publishing(self, ddev, mocker, monkeypatch):
        mocker.patch('ddev.release.placeholders.needs_placeholder', autospec=True, return_value=True)
        mocker.patch('ddev.release.placeholders.getpass.getpass', autospec=True)
        monkeypatch.delenv('DDEV_PYPI_TOKEN', raising=False)
        monkeypatch.delenv('ACTIONS_ID_TOKEN_REQUEST_URL', raising=False)
        monkeypatch.delenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', raising=False)

        result = ddev('release', 'placeholders', 'n8n')

        assert result.exit_code == 1
        assert 'No PyPI API token available' in result.output
