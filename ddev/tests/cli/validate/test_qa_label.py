# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

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


def _mock_labels(mocker, labels):
    return mocker.patch(
        'ddev.utils.github.GitHubManager.get_pull_request_labels',
        return_value=labels,
    )


@pytest.mark.parametrize('label', ['qa/required', 'qa/skip-qa'])
def test_passes_with_exactly_one_qa_label(ddev, pr_context, mocker, label):
    _mock_labels(mocker, [label, 'integration/foo'])

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 0, result.output
    assert 'Agent-release QA label set' in result.output


def test_fails_when_no_qa_label(ddev, pr_context, mocker):
    _mock_labels(mocker, ['integration/foo', 'documentation'])

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 1, result.output
    assert 'missing an Agent-release QA decision label' in result.output
    assert 'qa/required' in result.output
    assert 'qa/skip-qa' in result.output


def test_fails_when_both_qa_labels(ddev, pr_context, mocker):
    _mock_labels(mocker, ['qa/required', 'qa/skip-qa'])

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 1, result.output
    assert 'more than one Agent-release QA decision label' in result.output


def test_skips_outside_pull_request_context(ddev, monkeypatch, mocker):
    monkeypatch.delenv('GITHUB_EVENT_NAME', raising=False)
    get_labels = _mock_labels(mocker, [])

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 0, result.output
    assert 'Not running in a pull_request context' in result.output
    get_labels.assert_not_called()


def test_skips_on_fork_pull_request(ddev, fork_pr_context, mocker):
    get_labels = _mock_labels(mocker, [])

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 0, result.output
    assert 'fork' in result.output.lower()
    get_labels.assert_not_called()


@pytest.mark.parametrize(
    ('contents', 'create_file'),
    [
        pytest.param('{not valid json', True, id='malformed-json'),
        pytest.param('"a JSON string is not an object"', True, id='non-object-json'),
        pytest.param(None, False, id='missing-file'),
    ],
)
def test_aborts_when_event_file_is_unreadable(ddev, monkeypatch, tmp_path, mocker, contents, create_file):
    """Anything that prevents reading a valid event object must fail loudly, not silently skip."""
    event_path = tmp_path / 'event.json'
    if create_file:
        event_path.write_text(contents)
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'pull_request')
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event_path))
    get_labels = _mock_labels(mocker, [])

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 1, result.output
    assert 'Could not read GitHub event payload' in result.output, result.output
    get_labels.assert_not_called()


def test_skips_when_pr_number_is_missing(ddev, monkeypatch, tmp_path, mocker):
    """If the event payload lacks pull_request.number we can't fetch labels."""
    event = tmp_path / 'event.json'
    repo = {'repo': {'full_name': 'DataDog/integrations-core'}}
    event.write_text(json.dumps({'pull_request': {'head': repo, 'base': repo}}))
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'pull_request')
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event))
    monkeypatch.setenv('GITHUB_REPOSITORY', 'DataDog/integrations-core')
    get_labels = _mock_labels(mocker, [])

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 0, result.output
    assert 'Could not determine pull request number' in result.output
    get_labels.assert_not_called()


def test_aborts_when_head_or_base_repo_is_missing(ddev, monkeypatch, tmp_path, mocker):
    """An event payload without head/base repo info is malformed; don't silently skip."""
    event = tmp_path / 'event.json'
    event.write_text(json.dumps({'pull_request': {'number': 1, 'head': {}, 'base': {}}}))
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'pull_request')
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event))
    monkeypatch.delenv('GITHUB_REPOSITORY', raising=False)
    get_labels = _mock_labels(mocker, [])

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 1, result.output
    assert 'missing head/base repo information' in result.output
    get_labels.assert_not_called()


def test_aborts_when_pr_labels_cannot_be_fetched(ddev, pr_context, mocker):
    """A None return from the labels API call means we can't make a decision — fail closed."""
    _mock_labels(mocker, None)

    result = ddev('validate', 'qa-label')

    assert result.exit_code == 1, result.output
    assert 'Could not fetch pull request' in result.output
