# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import subprocess
import zipfile

import httpx
import pytest
from twine.commands.check import check as twine_check

from ddev.release.placeholders import PlaceholderPorts, publish_placeholders
from ddev.repo.core import Repository

GITHUB_TOKEN_URL = 'https://github-actions.example/token'
INSTALL_DOCS_URL = 'https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install'


@pytest.fixture
def repo(tmp_path):
    for name, package_name in (
        ('n8n', 'datadog-n8n'),
        ('kafka_consumer', 'datadog-kafka-consumer'),
        ('ddev', 'ddev'),
        ('datadog_checks_base', 'datadog-checks-base'),
    ):
        integration = tmp_path / name
        integration.mkdir()
        (integration / 'pyproject.toml').write_text(f'[project]\nname = "{package_name}"\n')
    subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
    return Repository('local', str(tmp_path))


def _pypi_version(version: str | None) -> httpx.Response:
    """Answer a PyPI JSON query: None means the name is missing (404)."""
    if version is None:
        return httpx.Response(404)
    return httpx.Response(200, json={'info': {'version': version}}, request=httpx.Request('GET', 'https://pypi.org'))


def _ports(**overrides) -> tuple[PlaceholderPorts, list[str]]:
    lines: list[str] = []
    return PlaceholderPorts(notify=lines.append, **overrides), lines


class TestPublishPlaceholders:
    def test_dry_run_selects_names_still_at_the_empty_placeholder(self, repo):
        ports, lines = _ports(http_get=lambda url, **kwargs: _pypi_version('0.0.1'))

        report = publish_placeholders(repo, ('n8n',), dry_run=True, ports=ports)

        assert report.selected == ['datadog-n8n']
        assert report.skipped == []
        assert lines == ['datadog-n8n']

    def test_dry_run_skips_names_that_already_have_a_release(self, repo):
        ports, lines = _ports(http_get=lambda url, **kwargs: _pypi_version('0.0.2'))

        report = publish_placeholders(repo, ('n8n',), dry_run=True, ports=ports)

        assert report.selected == []
        assert report.skipped == ['datadog-n8n']
        assert lines == ['  skip datadog-n8n (already published)']

    def test_resolves_every_name_spelling_once(self, repo):
        queries = []

        def http_get(url, **kwargs):
            queries.append(url)
            return _pypi_version('0.0.1')

        ports, _ = _ports(http_get=http_get)

        report = publish_placeholders(
            repo, ('n8n', 'Datadog-N8N', 'kafka-consumer', 'datadog_tokumx'), dry_run=True, ports=ports
        )

        assert report.selected == ['datadog-kafka-consumer', 'datadog-n8n', 'datadog-tokumx']
        assert len(queries) == 3

    def test_defaults_to_every_unclaimed_name_including_retired_ones(self, repo):
        queries = []

        def http_get(url, **kwargs):
            queries.append(url)
            name = url.rsplit('/', 2)[-2]
            state = {'datadog-tokumx': None, 'datadog-kafka-consumer': '0.0.2'}.get(name, '0.0.1')
            return _pypi_version(state)

        ports, _ = _ports(http_get=http_get)

        report = publish_placeholders(repo, dry_run=True, ports=ports)

        assert 'datadog-n8n' in report.selected
        assert 'datadog-tokumx' in report.selected
        assert 'datadog-oracle' in report.selected
        assert 'datadog-kafka-consumer' in report.skipped
        assert 'ddev' not in report.selected
        assert 'datadog-checks-base' not in report.selected
        assert len(queries) == 6  # both candidate packages plus the four retired names

    def test_publishes_a_built_placeholder_with_a_plain_token(self, repo, tmp_path, monkeypatch):
        monkeypatch.setenv('DDEV_PYPI_TOKEN', 'pypi-xxx')
        uploaded = []

        def upload(wheel, token):
            (tmp_path / wheel.name).write_bytes(wheel.read_bytes())
            uploaded.append((wheel.name, token))

        ports, lines = _ports(http_get=lambda url, **kwargs: _pypi_version('0.0.1'), upload=upload)

        report = publish_placeholders(repo, ('n8n',), ports=ports)

        assert report.published == {'datadog-n8n'}
        assert report.failed == {}
        assert lines[0] == '  ok datadog-n8n'
        assert lines[-1] == 'Published 1, failed 0'
        ((wheel_name, token),) = uploaded
        assert token == 'pypi-xxx'
        assert wheel_name.startswith('datadog_n8n-0.0.2-')
        assert not twine_check([str(tmp_path / wheel_name)])
        with zipfile.ZipFile(tmp_path / wheel_name) as archive:
            names = set(archive.namelist())
            (metadata_name,) = [name for name in names if name.endswith('METADATA')]
            metadata = archive.read(metadata_name).decode()
        assert 'datadog_n8n/__init__.py' in names
        assert 'Datadog reserves this name' in metadata
        assert INSTALL_DOCS_URL in metadata

    def test_publishes_through_trusted_publishing_minting_one_token_per_package(self, repo, monkeypatch):
        monkeypatch.delenv('DDEV_PYPI_TOKEN', raising=False)
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_URL', GITHUB_TOKEN_URL)
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', 'gh-secret')
        token_requests = []
        mints = []
        uploaded = []

        def http_get(url, **kwargs):
            if url == GITHUB_TOKEN_URL:
                token_requests.append(kwargs)
                return httpx.Response(200, json={'value': 'oidc-jwt'}, request=httpx.Request('GET', url))
            return _pypi_version('0.0.1')

        def http_post(url, **kwargs):
            mints.append(kwargs['json'])
            return httpx.Response(200, json={'token': 'pypi-minted'})

        def upload(wheel, token):
            uploaded.append((wheel.name, token))

        ports, lines = _ports(http_get=http_get, http_post=http_post, upload=upload)

        report = publish_placeholders(repo, ('n8n', 'datadog-tokumx'), ports=ports)

        assert report.published == {'datadog-n8n', 'datadog-tokumx'}
        assert report.failed == {}
        assert lines[-1] == 'Published 2, failed 0'
        assert mints == [{'token': 'oidc-jwt'}, {'token': 'oidc-jwt'}]
        assert token_requests[0]['headers'] == {'Authorization': 'bearer gh-secret'}
        assert token_requests[0]['params'] == {'audience': 'pypi'}
        assert [token for _, token in uploaded] == ['pypi-minted', 'pypi-minted']

    def test_a_refused_mint_fails_only_its_own_package(self, repo, monkeypatch):
        monkeypatch.delenv('DDEV_PYPI_TOKEN', raising=False)
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_URL', GITHUB_TOKEN_URL)
        monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', 'gh-secret')
        mint_responses = [
            httpx.Response(200, json={'token': 'pypi-minted'}),
            httpx.Response(400, text='invalid-publisher'),
        ]
        uploaded = []

        def http_get(url, **kwargs):
            if url == GITHUB_TOKEN_URL:
                return httpx.Response(200, json={'value': 'oidc-jwt'}, request=httpx.Request('GET', url))
            return _pypi_version('0.0.1')

        ports, lines = _ports(
            http_get=http_get,
            http_post=lambda url, **kwargs: mint_responses.pop(0),
            upload=lambda wheel, token: uploaded.append(wheel.name),
        )

        report = publish_placeholders(repo, ('n8n', 'datadog-tokumx'), ports=ports)

        assert len(report.published) == 1
        assert len(report.failed) == 1
        assert 'PyPI refused to mint an upload token for this workflow: invalid-publisher' in '\n'.join(lines)
        assert len(uploaded) == 1
        assert lines[-1] == 'Published 1, failed 1'

    def test_a_failed_build_reports_the_hatchling_output(self, repo, monkeypatch):
        monkeypatch.setenv('DDEV_PYPI_TOKEN', 'pypi-xxx')
        real_run = subprocess.run

        def fail_only_hatchling(command, **kwargs):
            if 'hatchling' not in command:
                return real_run(command, **kwargs)
            raise subprocess.CalledProcessError(1, command, stderr=b'invalid metadata')

        ports, lines = _ports(http_get=lambda url, **kwargs: _pypi_version('0.0.1'), run=fail_only_hatchling)

        report = publish_placeholders(repo, ('n8n',), ports=ports)

        assert list(report.failed) == ['datadog-n8n']
        assert '  FAIL datadog-n8n: hatchling build failed for datadog-n8n: invalid metadata' in lines

    def test_prompts_for_a_token_in_a_terminal(self, repo, monkeypatch):
        monkeypatch.delenv('DDEV_PYPI_TOKEN', raising=False)
        monkeypatch.delenv('ACTIONS_ID_TOKEN_REQUEST_URL', raising=False)
        monkeypatch.delenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', raising=False)
        prompts = []
        uploaded = []

        def prompt(text, hide_input):
            prompts.append((text, hide_input))
            return 'pypi-yyy'

        ports, _ = _ports(
            http_get=lambda url, **kwargs: _pypi_version('0.0.1'),
            upload=lambda wheel, token: uploaded.append(token),
            interactive=lambda: True,
            prompt=prompt,
        )

        publish_placeholders(repo, ('n8n',), ports=ports)

        assert prompts == [('PyPI API token: ', True)]
        assert uploaded == ['pypi-yyy']

    def test_the_environment_token_wins_over_the_prompt(self, repo, monkeypatch):
        monkeypatch.setenv('DDEV_PYPI_TOKEN', 'pypi-xxx')
        uploaded = []

        ports, _ = _ports(
            http_get=lambda url, **kwargs: _pypi_version('0.0.1'),
            upload=lambda wheel, token: uploaded.append(token),
            interactive=lambda: True,
            prompt=lambda text, hide_input: pytest.fail('should not prompt'),
        )

        publish_placeholders(repo, ('n8n',), ports=ports)

        assert uploaded == ['pypi-xxx']

    def test_aborts_without_a_token_or_trusted_publishing(self, repo, monkeypatch):
        monkeypatch.delenv('DDEV_PYPI_TOKEN', raising=False)
        monkeypatch.delenv('ACTIONS_ID_TOKEN_REQUEST_URL', raising=False)
        monkeypatch.delenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', raising=False)
        ports, _ = _ports(http_get=lambda url, **kwargs: _pypi_version('0.0.1'), interactive=lambda: False)

        with pytest.raises(ValueError, match='No PyPI API token available'):
            publish_placeholders(repo, ('n8n',), ports=ports)

    def test_unknown_name_aborts(self, repo):
        with pytest.raises(ValueError, match='Unknown integration or package name: not-an-integration'):
            publish_placeholders(repo, ('not-an-integration',))
