# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import subprocess
import zipfile

import httpx
import requests
import twine.repository

GITHUB_TOKEN_URL = 'https://github-actions.example/token'
PYPI_JSON_URL = 'https://pypi.org/pypi/{name}/json'
INSTALL_DOCS_URL = 'https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install'


def _pypi_version(version: str | None) -> httpx.Response:
    """Answer a PyPI JSON query: None means the name is missing (404)."""
    if version is None:
        return httpx.Response(404)
    return httpx.Response(200, json={'info': {'version': version}}, request=httpx.Request('GET', 'https://pypi.org'))


def _stub_pypi_uploads(mocker):
    """Stop twine at the index boundary and record what would be uploaded.

    The index says nothing is uploaded yet, reports no release URLs, and answers every
    upload with success after recording the wheel it was given.
    """
    wheels = []

    def upload(self, package):
        with zipfile.ZipFile(package.filename) as archive:
            names = set(archive.namelist())
            (metadata_name,) = [name for name in names if name.endswith('METADATA')]
            wheels.append((names, archive.read(metadata_name).decode()))
        response = requests.Response()
        response.status_code = 200
        response.reason = 'OK'
        response.url = 'https://upload.pypi.org/legacy/'
        return response

    mocker.patch.object(twine.repository.Repository, 'package_is_uploaded', autospec=True, return_value=False)
    uploaded = mocker.patch.object(twine.repository.Repository, 'upload', autospec=True, side_effect=upload)
    mocker.patch.object(twine.repository.Repository, 'release_urls', autospec=True, return_value=[])
    return uploaded, wheels


class TestPlaceholdersCommand:
    def test_dry_run_lists_names_still_at_the_empty_placeholder(self, ddev, mocker):
        mocker.patch('httpx.get', autospec=True, return_value=_pypi_version('0.0.1'))

        result = ddev('release', 'placeholders', 'n8n', '--dry-run')

        assert result.exit_code == 0, result.output
        assert 'datadog-n8n' in result.output

    def test_dry_run_skips_names_that_already_have_a_release(self, ddev, mocker):
        mocker.patch('httpx.get', autospec=True, return_value=_pypi_version('0.0.2'))

        result = ddev('release', 'placeholders', 'n8n', '--dry-run')

        assert result.exit_code == 0, result.output
        assert 'skip datadog-n8n (already published)' in result.output
        assert 'Nothing to publish.' in result.output

    def test_resolves_every_name_spelling_once(self, ddev, mocker):
        httpx_get = mocker.patch('httpx.get', autospec=True, return_value=_pypi_version('0.0.1'))

        result = ddev('release', 'placeholders', 'n8n', 'Datadog-N8N', 'kafka-consumer', 'datadog_tokumx', '--dry-run')

        assert result.exit_code == 0, result.output
        assert httpx_get.call_count == 3
        for name in ('datadog-n8n', 'datadog-kafka-consumer', 'datadog-tokumx'):
            assert name in result.output

    def test_defaults_to_every_unclaimed_name_including_retired_ones(self, ddev, mocker):
        def pypi_json(url, **kwargs):
            name = url.rsplit('/', 2)[-2]
            state = {'datadog-tokumx': None, 'datadog-active-directory': '0.0.2'}.get(name, '0.0.1')
            return _pypi_version(state)

        httpx_get = mocker.patch('httpx.get', autospec=True, side_effect=pypi_json)

        result = ddev('release', 'placeholders', '--dry-run')

        assert result.exit_code == 0, result.output
        assert 'datadog-n8n' in result.output
        assert 'datadog-tokumx' in result.output
        assert 'datadog-active-directory' not in result.output
        assert 'datadog-checks-base' not in result.output
        assert httpx_get.call_count > 200

    def test_publishes_a_built_placeholder_with_a_plain_token(self, ddev, mocker, monkeypatch):
        monkeypatch.setenv('DDEV_PYPI_TOKEN', 'pypi-xxx')
        mocker.patch('httpx.get', autospec=True, return_value=_pypi_version('0.0.1'))
        uploaded, wheels = _stub_pypi_uploads(mocker)

        result = ddev('release', 'placeholders', 'n8n')

        assert result.exit_code == 0, result.output
        assert 'ok datadog-n8n' in result.output
        assert 'Published 1, failed 0' in result.output
        repository, package = uploaded.call_args.args
        assert repository.url == 'https://upload.pypi.org/legacy/'
        assert repository.session.auth == ('__token__', 'pypi-xxx')
        assert package.basefilename.startswith('datadog_n8n-0.0.2-')
        (names, metadata) = wheels[0]
        assert 'datadog_n8n/__init__.py' in names
        assert 'Datadog reserves this name' in metadata
        assert INSTALL_DOCS_URL in metadata

    def test_publishes_through_trusted_publishing_minting_one_token_per_package(self, ddev, mocker, monkeypatch):
        monkeypatch.delenv('DDEV_PYPI_TOKEN', raising=False)
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_URL', GITHUB_TOKEN_URL)
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', 'gh-secret')

        def get(url, **kwargs):
            if url == GITHUB_TOKEN_URL:
                return httpx.Response(200, json={'value': 'oidc-jwt'}, request=httpx.Request('GET', url))
            return _pypi_version('0.0.1')

        httpx_get = mocker.patch('httpx.get', autospec=True, side_effect=get)
        httpx_post = mocker.patch(
            'httpx.post', autospec=True, return_value=httpx.Response(200, json={'token': 'pypi-minted'})
        )
        uploaded, _ = _stub_pypi_uploads(mocker)

        result = ddev('release', 'placeholders', 'n8n', 'datadog-tokumx')

        assert result.exit_code == 0, result.output
        assert 'Published 2, failed 0' in result.output
        assert httpx_post.call_count == 2
        assert [call.kwargs['json'] for call in httpx_post.call_args_list] == [
            {'token': 'oidc-jwt'},
            {'token': 'oidc-jwt'},
        ]
        token_requests = [call for call in httpx_get.call_args_list if call.args[0] == GITHUB_TOKEN_URL]
        assert len(token_requests) == 2
        assert token_requests[0].kwargs['headers'] == {'Authorization': 'bearer gh-secret'}
        assert token_requests[0].kwargs['params'] == {'audience': 'pypi'}
        assert uploaded.call_count == 2
        assert all(call.args[0].session.auth == ('__token__', 'pypi-minted') for call in uploaded.call_args_list)

    def test_a_refused_mint_fails_only_its_own_package(self, ddev, mocker, monkeypatch):
        monkeypatch.delenv('DDEV_PYPI_TOKEN', raising=False)
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_URL', GITHUB_TOKEN_URL)
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', 'gh-secret')

        def get(url, **kwargs):
            if url == GITHUB_TOKEN_URL:
                return httpx.Response(200, json={'value': 'oidc-jwt'}, request=httpx.Request('GET', url))
            return _pypi_version('0.0.1')

        mint_responses = [
            httpx.Response(200, json={'token': 'pypi-minted'}),
            httpx.Response(400, text='invalid-publisher'),
        ]
        mocker.patch('httpx.get', autospec=True, side_effect=get)
        mocker.patch('httpx.post', autospec=True, side_effect=lambda url, **kwargs: mint_responses.pop(0))
        uploaded, _ = _stub_pypi_uploads(mocker)

        result = ddev('release', 'placeholders', 'n8n', 'datadog-tokumx')

        assert result.exit_code == 1
        assert 'Published 1, failed 1' in result.output
        assert 'ok ' in result.output
        assert 'PyPI refused to mint an upload token for this workflow: invalid-publisher' in result.output
        assert uploaded.call_count == 1

    def test_a_failed_build_reports_the_hatchling_output(self, ddev, mocker, monkeypatch):
        monkeypatch.setenv('DDEV_PYPI_TOKEN', 'pypi-xxx')
        mocker.patch('httpx.get', autospec=True, return_value=_pypi_version('0.0.1'))
        real_run = subprocess.run

        def fail_only_hatchling(command, **kwargs):
            if 'hatchling' not in command:
                return real_run(command, **kwargs)
            raise subprocess.CalledProcessError(1, command, stderr=b'invalid metadata')

        mocker.patch('subprocess.run', autospec=True, side_effect=fail_only_hatchling)

        result = ddev('release', 'placeholders', 'n8n')

        assert result.exit_code == 1
        assert 'FAIL datadog-n8n: hatchling build failed for datadog-n8n: invalid metadata' in result.output
        assert 'Published 0, failed 1' in result.output

    def test_aborts_without_a_token_or_trusted_publishing(self, ddev, mocker, monkeypatch):
        mocker.patch('httpx.get', autospec=True, return_value=_pypi_version('0.0.1'))
        monkeypatch.delenv('DDEV_PYPI_TOKEN', raising=False)
        monkeypatch.delenv('ACTIONS_ID_TOKEN_REQUEST_URL', raising=False)
        monkeypatch.delenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', raising=False)

        result = ddev('release', 'placeholders', 'n8n')

        assert result.exit_code == 1
        assert 'No PyPI API token available' in result.output

    def test_unknown_name_aborts(self, ddev):
        result = ddev('release', 'placeholders', 'not-an-integration', '--dry-run')

        assert result.exit_code == 1
        assert 'Unknown integration or package name: not-an-integration' in result.output
