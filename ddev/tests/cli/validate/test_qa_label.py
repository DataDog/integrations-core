# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from unittest.mock import MagicMock

import pytest


def _write_event(tmp_path, head_repo='DataDog/integrations-core', number=1234):
    payload = {
        'pull_request': {
            'number': number,
            'head': {'repo': {'full_name': head_repo}},
            'base': {'repo': {'full_name': 'DataDog/integrations-core'}},
        },
    }
    event_path = tmp_path / 'event.json'
    event_path.write_text(json.dumps(payload))
    return event_path


@pytest.fixture
def pr_context(monkeypatch, tmp_path):
    """Pretend ddev is running inside a GitHub Actions pull_request event."""
    event_path = _write_event(tmp_path)
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'pull_request')
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event_path))
    monkeypatch.setenv('GITHUB_REPOSITORY', 'DataDog/integrations-core')


@pytest.fixture
def fork_pr_context(monkeypatch, tmp_path):
    event_path = _write_event(tmp_path, head_repo='someone-else/integrations-core')
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'pull_request')
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event_path))
    monkeypatch.setenv('GITHUB_REPOSITORY', 'DataDog/integrations-core')


def _mock_pr_with_labels(mocker, labels):
    pr = MagicMock()
    pr.labels = sorted(labels)
    return mocker.patch('ddev.utils.github.GitHubManager.get_pull_request_by_number', return_value=pr)


@pytest.mark.parametrize('label', ['qa/required', 'qa/skip-qa'])
def test_passes_with_exactly_one_qa_label(ddev, pr_context, mocker, label):
    _mock_pr_with_labels(mocker, [label, 'integration/foo'])

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 0, result.output
    assert 'QA label set' in result.output


def test_fails_when_no_qa_label(ddev, pr_context, mocker):
    _mock_pr_with_labels(mocker, ['integration/foo', 'documentation'])

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 1, result.output
    assert 'No QA decision label set' in result.output
    assert 'qa/required' in result.output
    assert 'qa/skip-qa' in result.output


def test_fails_when_both_qa_labels(ddev, pr_context, mocker):
    _mock_pr_with_labels(mocker, ['qa/required', 'qa/skip-qa'])

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 1, result.output
    assert 'more than one QA decision label' in result.output


def test_skips_outside_pull_request_context(ddev, monkeypatch, mocker):
    monkeypatch.delenv('GITHUB_EVENT_NAME', raising=False)
    get_pr = _mock_pr_with_labels(mocker, [])

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 0, result.output
    assert 'Not running in a pull_request context' in result.output
    get_pr.assert_not_called()


def test_skips_on_fork_pull_request(ddev, fork_pr_context, mocker):
    get_pr = _mock_pr_with_labels(mocker, [])

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 0, result.output
    assert 'fork' in result.output.lower()
    get_pr.assert_not_called()
