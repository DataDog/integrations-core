# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest

CHECKLIST_ITEMS = ('First required item', 'Second required item')
VALID_BODY = '## Checklist before requesting review\n\n' + '\n'.join(f'- [x] {item}' for item in CHECKLIST_ITEMS)


def _write_event(tmp_path, **overrides):
    pull_request = {
        'body': VALID_BODY,
        'title': 'Improve PR validation',
        'user': {'login': 'human-author'},
        'created_at': '2026-10-03T00:00:00Z',
    }
    pull_request.update(overrides)
    event_path = tmp_path / 'event.json'
    event_path.write_text(json.dumps({'pull_request': pull_request}))
    return event_path


@pytest.fixture
def pr_context(monkeypatch, tmp_path):
    event_path = _write_event(tmp_path)
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'pull_request')
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event_path))
    return event_path


@pytest.fixture
def pr_template(fake_repo):
    template_path = fake_repo.path / '.github' / 'PULL_REQUEST_TEMPLATE.md'
    template_path.write_text(
        '## Checklist before requesting review\n\n'
        '- [ ] First required item\n'
        '- [ ] Second required item\n\n'
        '## What does this PR do?\n'
    )
    return template_path


def test_skips_outside_pull_request_context(ddev, monkeypatch):
    monkeypatch.delenv('GITHUB_EVENT_NAME', raising=False)

    result = ddev('validate', 'pr-description')

    assert result.exit_code == 0, result.output
    assert 'Not running in a pull_request context' in result.output


def test_skips_without_event_path(ddev, monkeypatch):
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'pull_request')
    monkeypatch.delenv('GITHUB_EVENT_PATH', raising=False)

    result = ddev('validate', 'pr-description')

    assert result.exit_code == 0, result.output
    assert 'GITHUB_EVENT_PATH is not set' in result.output


def test_passes_with_ticked_checklist(ddev, pr_context, pr_template):
    result = ddev('validate', 'pr-description')

    assert result.exit_code == 0, result.output
    assert 'PR description check passed' in result.output


def test_fails_with_unticked_item(ddev, pr_context, pr_template):
    event = json.loads(pr_context.read_text())
    event['pull_request']['body'] = (
        '## Checklist before requesting review\n\n- [x] First required item\n- [ ] Second required item'
    )
    pr_context.write_text(json.dumps(event))

    result = ddev('validate', 'pr-description')

    assert result.exit_code == 1, result.output
    assert 'Unchecked checklist item: Second required item' in result.output


def test_fails_with_replaced_items(ddev, pr_context, pr_template):
    event = json.loads(pr_context.read_text())
    event['pull_request']['body'] = '## Checklist before requesting review\n\n- [x] arbitrary'
    pr_context.write_text(json.dumps(event))

    result = ddev('validate', 'pr-description')

    assert result.exit_code == 1, result.output
    assert 'Missing checklist item (restore it from the template): First required item' in result.output
    assert 'Missing checklist item (restore it from the template): Second required item' in result.output


def test_item_hidden_in_html_comment_is_missing(ddev, pr_context, pr_template):
    event = json.loads(pr_context.read_text())
    event['pull_request']['body'] = (
        '## Checklist before requesting review\n\n<!--\n- [x] First required item\n-->\n- [x] Second required item'
    )
    pr_context.write_text(json.dumps(event))

    result = ddev('validate', 'pr-description')

    assert result.exit_code == 1, result.output
    assert 'Missing checklist item (restore it from the template): First required item' in result.output


def test_fails_when_visible_description_is_too_long(ddev, pr_context, pr_template):
    visible_prefix = f'{VALID_BODY}\n'
    visible_body = visible_prefix + ('x' * (3001 - len(visible_prefix)))
    event = json.loads(pr_context.read_text())
    event['pull_request']['body'] = f'{visible_body}<!--{"hidden" * 1000}-->'
    pr_context.write_text(json.dumps(event))

    result = ddev('validate', 'pr-description')

    assert result.exit_code == 1, result.output
    assert 'PR description is 3001 characters; maximum is 3000.' in result.output


@pytest.mark.parametrize(
    ('overrides', 'reason'),
    [
        pytest.param({'user': {'login': 'dependabot[bot]'}}, 'bot author dependabot[bot]', id='bot-author'),
        pytest.param({'title': '[release] datadog-foo 1.2.3'}, 'release PR', id='release-title'),
        pytest.param(
            {'created_at': '2026-10-01T23:59:59Z'},
            'PR opened before 2026-10-02',
            id='before-enforcement',
        ),
    ],
)
def test_skips_exempt_pull_requests(ddev, monkeypatch, tmp_path, pr_template, overrides, reason):
    event_path = _write_event(tmp_path, **overrides)
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'pull_request')
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event_path))

    result = ddev('validate', 'pr-description')

    assert result.exit_code == 0, result.output
    assert reason in result.output


@pytest.mark.parametrize(
    'template_contents', [None, '# Template without a checklist\n'], ids=['missing', 'no-checklist']
)
def test_skips_without_template_checklist(ddev, pr_context, fake_repo, template_contents):
    if template_contents is not None:
        template_path = fake_repo.path / '.github' / 'PULL_REQUEST_TEMPLATE.md'
        template_path.write_text(template_contents)

    result = ddev('validate', 'pr-description')

    assert result.exit_code == 0, result.output
    assert 'no checklist items found' in result.output.lower()


def test_null_body_fails_with_missing_items(ddev, monkeypatch, tmp_path, pr_template):
    event_path = _write_event(tmp_path, body=None)
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'pull_request')
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event_path))

    result = ddev('validate', 'pr-description')

    assert result.exit_code == 1, result.output
    assert 'Missing checklist item (restore it from the template): First required item' in result.output
    assert 'Missing checklist item (restore it from the template): Second required item' in result.output
