# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
import signal
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Callable

import httpx
import pytest
from twine.commands.check import check as twine_check

from ddev.release.placeholders import PlaceholderPorts, publish_placeholders
from ddev.repo.core import Repository

GITHUB_TOKEN_URL = 'https://github-actions.example/token?api-version=2.0'
INSTALL_DOCS_URL = 'https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install'

REPO_PACKAGES = {
    'n8n': 'datadog-n8n',
    'kafka_consumer': 'datadog-kafka-consumer',
    'ddev': 'ddev',
    'datadog_checks_base': 'datadog-checks-base',
}


def _make_repo(tmp_path: Path) -> Repository:
    for name, package_name in REPO_PACKAGES.items():
        integration = tmp_path / name
        integration.mkdir()
        (integration / 'pyproject.toml').write_text(f'[project]\nname = "{package_name}"\n')
    (tmp_path / '.ddev').mkdir()
    (tmp_path / '.ddev' / 'config.toml').write_text(
        '[overrides.is-integration]\nddev = false\ndatadog_checks_base = false\n'
    )
    subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
    return Repository('local', str(tmp_path))


def _pypi_version(version: str | None) -> httpx.Response:
    """Answer a PyPI JSON query: None means the name is missing (404)."""
    if version is None:
        return httpx.Response(404)
    return httpx.Response(200, json={'info': {'version': version}}, request=httpx.Request('GET', 'https://pypi.org'))


def _pypi_states(states: dict[str, str | None] | None = None, queries: list[str] | None = None):
    """A PyPI reporting custom per-package versions, None meaning missing; others report 0.0.1."""
    states = states or {}

    def http_get(url, **kwargs):
        if queries is not None:
            queries.append(url)
        name = url.rsplit('/', 2)[-2]
        return _pypi_version(states.get(name, '0.0.1'))

    return http_get


def _trusted_publishing(monkeypatch) -> tuple[list[dict], Callable[..., httpx.Response]]:
    """Configure the GitHub Actions OIDC environment for trusted publishing.

    Returns the list recording the GitHub token requests, and the HTTP fake answering them
    and the PyPI JSON queries.
    """
    monkeypatch.delenv('DDEV_PYPI_TOKEN', raising=False)
    monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_URL', GITHUB_TOKEN_URL)
    monkeypatch.setenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', 'gh-secret')
    token_requests = []

    def http_get(url, **kwargs):
        if url == GITHUB_TOKEN_URL:
            token_requests.append(kwargs)
            return httpx.Response(200, json={'value': 'oidc-jwt'}, request=httpx.Request('GET', url))
        return _pypi_version('0.0.1')

    return token_requests, http_get


def _recording_upload(save: Path | None = None):
    """An upload port recording (wheel name, token) pairs, saving the wheel to `save` when given."""
    uploads = []

    def upload(wheel, token):
        if save is not None:
            (save / wheel.name).write_bytes(wheel.read_bytes())
        uploads.append((wheel.name, token))

    return upload, uploads


def _ports(**overrides) -> tuple[PlaceholderPorts, list[str]]:
    lines: list[str] = []
    return PlaceholderPorts(notify=lambda level, text: lines.append(text), **overrides), lines


def _failing_hatchling(stderr: bytes):
    """A build runner where every hatchling invocation fails; other commands run normally."""
    real_run = subprocess.run

    def run(command, **kwargs):
        if 'hatchling' not in command:
            return real_run(command, **kwargs)
        raise subprocess.CalledProcessError(1, command, stderr=stderr)

    return run


def test_dry_run_selects_names_still_at_the_empty_placeholder(tmp_path):
    ports, lines = _ports(http_get=_pypi_states())

    report = publish_placeholders(_make_repo(tmp_path), ('n8n',), dry_run=True, ports=ports)

    assert report.selected == ['datadog-n8n']


def test_dry_run_skips_names_that_already_have_a_release(tmp_path):
    ports, lines = _ports(http_get=_pypi_states({'datadog-n8n': '0.0.2'}))

    report = publish_placeholders(_make_repo(tmp_path), ('n8n',), dry_run=True, ports=ports)

    assert report.skipped == ['datadog-n8n']
    assert lines == ['Checking 1 names on PyPI...', '  skip datadog-n8n (already published)']


def test_resolves_every_name_spelling_once(tmp_path):
    queries: list[str] = []
    ports, _ = _ports(http_get=_pypi_states(queries=queries))

    report = publish_placeholders(
        _make_repo(tmp_path), ('n8n', 'Datadog-N8N', 'kafka-consumer', 'datadog_tokumx'), dry_run=True, ports=ports
    )

    assert report.selected == ['datadog-kafka-consumer', 'datadog-n8n', 'datadog-tokumx']
    assert len(queries) == 3


def test_defaults_to_every_unclaimed_name_including_retired_ones(tmp_path):
    queries: list[str] = []
    ports, _ = _ports(http_get=_pypi_states({'datadog-tokumx': None, 'datadog-kafka-consumer': '0.0.2'}, queries))

    report = publish_placeholders(_make_repo(tmp_path), dry_run=True, ports=ports)

    assert 'datadog-n8n' in report.selected
    assert 'datadog-tokumx' in report.selected
    assert 'datadog-datadog_checks_dependency_provider' in report.selected
    assert 'datadog-kafka-consumer' in report.skipped
    assert 'ddev' not in report.selected
    assert 'datadog-checks-base' not in report.selected
    assert len(queries) == 7  # both candidate packages plus the five kept names


def test_publishes_a_built_placeholder_with_a_plain_token(tmp_path, monkeypatch):
    monkeypatch.setenv('DDEV_PYPI_TOKEN', 'pypi-xxx')
    upload, uploads = _recording_upload(save=tmp_path)
    ports, lines = _ports(http_get=_pypi_states(), upload=upload)

    report = publish_placeholders(_make_repo(tmp_path), ('n8n',), ports=ports)

    assert report.published == {'datadog-n8n'}
    assert lines == ['Checking 1 names on PyPI...', '  ok datadog-n8n', 'Published 1, failed 0']
    ((wheel_name, token),) = uploads
    assert token == 'pypi-xxx'
    assert wheel_name.startswith('datadog_n8n-0.0.2-')
    assert not twine_check([str(tmp_path / wheel_name)])
    with zipfile.ZipFile(tmp_path / wheel_name) as archive:
        names = set(archive.namelist())
        (metadata_name,) = [name for name in names if name.endswith('METADATA')]
        metadata = archive.read(metadata_name).decode()
    assert 'datadog_n8n/__init__.py' in names
    assert INSTALL_DOCS_URL in metadata


def test_publishes_through_trusted_publishing_minting_one_token_per_package(tmp_path, monkeypatch):
    token_requests, http_get = _trusted_publishing(monkeypatch)
    mints = []

    def http_post(url, **kwargs):
        mints.append(kwargs['json'])
        return httpx.Response(200, json={'token': 'pypi-minted'})

    upload, uploads = _recording_upload()
    ports, _ = _ports(http_get=http_get, http_post=http_post, upload=upload)

    report = publish_placeholders(_make_repo(tmp_path), ('n8n', 'datadog-tokumx'), ports=ports)

    assert report.published == {'datadog-n8n', 'datadog-tokumx'}
    assert mints == [{'token': 'oidc-jwt'}, {'token': 'oidc-jwt'}]
    assert token_requests[0]['headers'] == {'Authorization': 'bearer gh-secret'}
    assert token_requests[0]['params'] == {'api-version': '2.0', 'audience': 'pypi'}
    assert [token for _, token in uploads] == ['pypi-minted', 'pypi-minted']


def test_a_refused_mint_fails_only_its_own_package(tmp_path, monkeypatch):
    _, http_get = _trusted_publishing(monkeypatch)
    mint_responses = [
        httpx.Response(200, json={'token': 'pypi-minted'}),
        httpx.Response(400, text='invalid-publisher'),
    ]
    upload, uploads = _recording_upload()
    ports, lines = _ports(
        http_get=http_get,
        http_post=lambda url, **kwargs: mint_responses.pop(0),
        upload=upload,
    )

    report = publish_placeholders(_make_repo(tmp_path), ('n8n', 'datadog-tokumx'), ports=ports)

    assert len(report.published) == 1
    assert len(report.failed) == 1
    assert 'PyPI refused to mint an upload token for this workflow: invalid-publisher' in '\n'.join(lines)
    assert len(uploads) == 1


def test_a_failed_build_reports_the_hatchling_output(tmp_path, monkeypatch):
    monkeypatch.setenv('DDEV_PYPI_TOKEN', 'pypi-xxx')
    ports, lines = _ports(http_get=_pypi_states(), run=_failing_hatchling(b'invalid metadata'))

    report = publish_placeholders(_make_repo(tmp_path), ('n8n',), ports=ports)

    assert list(report.failed) == ['datadog-n8n']
    assert '  FAIL datadog-n8n: hatchling build failed for datadog-n8n: invalid metadata' in lines


def test_prompts_for_a_token_in_a_terminal(tmp_path, monkeypatch):
    monkeypatch.delenv('DDEV_PYPI_TOKEN', raising=False)
    prompts = []

    def prompt(text, hide_input):
        prompts.append((text, hide_input))
        return 'pypi-yyy'

    upload, uploads = _recording_upload()
    ports, _ = _ports(http_get=_pypi_states(), upload=upload, interactive=lambda: True, prompt=prompt)

    publish_placeholders(_make_repo(tmp_path), ('n8n',), ports=ports)

    assert prompts == [('PyPI API token: ', True)]
    assert [token for _, token in uploads] == ['pypi-yyy']


def test_the_environment_token_wins_over_the_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv('DDEV_PYPI_TOKEN', 'pypi-xxx')
    upload, uploads = _recording_upload()
    ports, _ = _ports(
        http_get=_pypi_states(),
        upload=upload,
        interactive=lambda: True,
        prompt=lambda text, hide_input: pytest.fail('should not prompt'),
    )

    publish_placeholders(_make_repo(tmp_path), ('n8n',), ports=ports)

    assert [token for _, token in uploads] == ['pypi-xxx']


def test_command_aborts_on_unknown_names(ddev):
    result = ddev('release', 'placeholders', 'not-an-integration')

    assert result.exit_code == 1
    assert 'Unknown integration or package name: not-an-integration' in result.output


def test_command_aborts_without_a_token_or_trusted_publishing(ddev, mocker, monkeypatch):
    mocker.patch('httpx.get', autospec=True, return_value=_pypi_version('0.0.1'))
    monkeypatch.delenv('DDEV_PYPI_TOKEN', raising=False)
    monkeypatch.delenv('ACTIONS_ID_TOKEN_REQUEST_URL', raising=False)
    monkeypatch.delenv('ACTIONS_ID_TOKEN_REQUEST_TOKEN', raising=False)

    result = ddev('--no-interactive', 'release', 'placeholders', 'n8n')

    assert result.exit_code == 1
    assert 'No PyPI API token available' in result.output


def test_command_lists_selected_names_on_dry_run(ddev, mocker):
    mocker.patch('httpx.get', autospec=True, return_value=_pypi_version('0.0.1'))

    result = ddev('release', 'placeholders', 'n8n', '--dry-run')

    assert result.exit_code == 0
    assert 'datadog-n8n' in result.stdout
    assert 'Nothing to publish.' not in result.output


def test_command_reports_nothing_to_publish(ddev, mocker):
    mocker.patch('httpx.get', autospec=True, return_value=_pypi_version('0.0.2'))

    result = ddev('release', 'placeholders', 'n8n', '--dry-run')

    assert result.exit_code == 0
    assert 'Nothing to publish.' in result.output


def test_command_fails_when_the_pypi_check_errors(ddev, mocker):
    mocker.patch('httpx.get', autospec=True, side_effect=httpx.ConnectError('connection refused'))

    result = ddev('--no-interactive', 'release', 'placeholders', 'n8n')

    assert result.exit_code == 1
    assert 'FAIL datadog-n8n: PyPI check failed' in result.output
    assert 'Nothing to publish.' not in result.output


@pytest.mark.skipif(sys.platform == 'win32', reason='sends SIGINT to the process')
def test_a_stopped_run_fails_rather_than_reporting_success(tmp_path, monkeypatch):
    monkeypatch.setenv('DDEV_PYPI_TOKEN', 'pypi-xxx')

    def upload(wheel, token):
        os.kill(os.getpid(), signal.SIGINT)

    ports, _ = _ports(http_get=_pypi_states(), upload=upload)

    with pytest.raises(ValueError, match='Publishing placeholders stopped: cancelled'):
        publish_placeholders(_make_repo(tmp_path), ('n8n',), ports=ports)
