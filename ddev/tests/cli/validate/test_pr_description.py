# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest

from ddev.cli.validate.pr_description import _check_pr_description, _checklist, _skip_reason

CHECKLIST_ITEMS = ['First required item', 'Second required item']
TEMPLATE = (
    '## Checklist before requesting review\n\n'
    '- [ ] First required item\n'
    '  <!-- How to verify: something. -->\n'
    '- [ ] Second required item\n\n'
    '## What does this PR do?\n'
)
VALID_BODY = '## Checklist before requesting review\n\n' + '\n'.join(f'- [x] {item}' for item in CHECKLIST_ITEMS)


def test_checklist_reads_template_items():
    assert _checklist(TEMPLATE) == {'First required item': False, 'Second required item': False}


def test_valid_body_has_no_errors():
    assert _check_pr_description(VALID_BODY, CHECKLIST_ITEMS) == []


def test_unticked_item_is_reported():
    body = VALID_BODY.replace('- [x] Second', '- [ ] Second')

    assert _check_pr_description(body, CHECKLIST_ITEMS) == ['Unchecked checklist item: Second required item']


@pytest.mark.parametrize(
    'body',
    [
        pytest.param('## Checklist before requesting review\n\n- [x] arbitrary', id='replaced'),
        pytest.param('', id='empty'),
    ],
)
def test_missing_items_are_reported(body):
    assert _check_pr_description(body, CHECKLIST_ITEMS) == [
        f'Missing checklist item (restore it from the template): {item}' for item in CHECKLIST_ITEMS
    ]


def test_item_hidden_in_html_comment_is_missing():
    body = VALID_BODY.replace('- [x] First required item', '<!--\n- [x] First required item\n-->')

    assert _check_pr_description(body, CHECKLIST_ITEMS) == [
        'Missing checklist item (restore it from the template): First required item'
    ]


def test_length_counts_visible_text_only():
    hidden = f'<!--{"hidden" * 1000}-->'
    at_limit = f'{VALID_BODY}\n' + 'x' * (3000 - len(VALID_BODY) - 1)

    assert _check_pr_description(at_limit + hidden, CHECKLIST_ITEMS) == []
    assert _check_pr_description(at_limit + 'x' + hidden, CHECKLIST_ITEMS) == [
        'PR description is 3001 characters; maximum is 3000. Trim the description before requesting review.'
    ]


@pytest.mark.parametrize(
    ('author', 'author_type', 'title', 'created_at', 'reason'),
    [
        pytest.param('human', 'User', 'Fix a bug', '2026-10-03T00:00:00Z', None, id='human'),
        pytest.param('some-bot', 'User', 'Fix a bug', '2026-10-03T00:00:00Z', None, id='bot-like-name-is-a-user'),
        pytest.param(
            'dependabot[bot]', 'Bot', 'Bump x', '2026-10-03T00:00:00Z', 'bot author dependabot[bot]', id='bot'
        ),
        pytest.param('Copilot', 'Bot', 'Fix a bug', '2026-10-03T00:00:00Z', 'bot author Copilot', id='copilot'),
        pytest.param('human', 'User', '[Release] Bumped x', '2026-10-03T00:00:00Z', 'release PR', id='release'),
        pytest.param(
            'human', 'User', 'Fix a bug', '2026-10-01T23:59:59Z', 'PR opened before 2026-10-02', id='before-cutoff'
        ),
        pytest.param('human', 'User', 'Fix a bug', None, None, id='no-created-at'),
    ],
)
def test_skip_reason(author, author_type, title, created_at, reason):
    result = _skip_reason(author, author_type, title, created_at)

    if reason is None:
        assert result is None
    else:
        assert result is not None
        assert reason in result


@pytest.fixture
def pr_template(fake_repo):
    template_path = fake_repo.path / '.github' / 'PULL_REQUEST_TEMPLATE.md'
    template_path.write_text(TEMPLATE)
    return template_path


@pytest.fixture
def current_body(mocker):
    """Mock the PR description fetched from the GitHub API; defaults to a valid body."""
    return mocker.patch('ddev.utils.github.GitHubManager.get_pull_request_body', return_value=VALID_BODY)


def _event_args(tmp_path, **overrides):
    pull_request = {
        'number': 1234,
        'body': VALID_BODY,
        'title': 'Improve PR validation',
        'user': {'login': 'human-author', 'type': 'User'},
        'created_at': '2026-10-03T00:00:00Z',
        **overrides,
    }
    event_path = tmp_path / 'event.json'
    event_path.write_text(json.dumps({'pull_request': pull_request}))
    return ['--event-name', 'pull_request', '--event-path', str(event_path)]


def test_cli_passes_with_ticked_checklist(ddev, tmp_path, pr_template, current_body):
    result = ddev('validate', 'pr-description', *_event_args(tmp_path))

    assert result.exit_code == 0, result.output
    assert 'PR description check passed' in result.output
    current_body.assert_called_once_with(1234)


def test_cli_fails_and_reports_errors(ddev, tmp_path, pr_template, current_body):
    current_body.return_value = ''

    result = ddev('validate', 'pr-description', *_event_args(tmp_path))

    assert result.exit_code == 1, result.output
    assert 'Missing checklist item (restore it from the template): First required item' in result.output


def test_cli_uses_current_description_over_stale_payload(ddev, tmp_path, pr_template, current_body):
    stale_body = VALID_BODY.replace('- [x] Second', '- [ ] Second')

    result = ddev('validate', 'pr-description', *_event_args(tmp_path, body=stale_body))

    assert result.exit_code == 0, result.output
    assert 'PR description check passed' in result.output


def test_cli_falls_back_to_payload_when_fetch_fails(ddev, tmp_path, pr_template, current_body):
    current_body.return_value = None
    stale_body = VALID_BODY.replace('- [x] Second', '- [ ] Second')

    result = ddev('validate', 'pr-description', *_event_args(tmp_path, body=stale_body))

    assert result.exit_code == 1, result.output
    assert 'Could not fetch the current PR description' in result.output
    assert 'Unchecked checklist item: Second required item' in result.output


def test_cli_logs_skip_reason(ddev, tmp_path, pr_template):
    args = _event_args(tmp_path, user={'login': 'renovate[bot]', 'type': 'Bot'})

    result = ddev('validate', 'pr-description', *args)

    assert result.exit_code == 0, result.output
    assert 'Skipping PR description check: bot author renovate[bot].' in result.output


@pytest.mark.parametrize(
    ('args', 'message'),
    [
        pytest.param(['--event-name', 'push', '--event-path', ''], 'Not running in a pull_request context', id='push'),
        pytest.param(
            ['--event-name', 'pull_request', '--event-path', ''], 'No GitHub event payload path given', id='no-path'
        ),
    ],
)
def test_cli_skips_outside_pull_request_events(ddev, args, message):
    result = ddev('validate', 'pr-description', *args)

    assert result.exit_code == 0, result.output
    assert message in result.output


@pytest.mark.parametrize('template', [None, '# Template without a checklist\n'], ids=['missing', 'no-checklist'])
def test_cli_skips_without_template_checklist(ddev, tmp_path, fake_repo, template):
    if template is not None:
        (fake_repo.path / '.github' / 'PULL_REQUEST_TEMPLATE.md').write_text(template)

    result = ddev('validate', 'pr-description', *_event_args(tmp_path))

    assert result.exit_code == 0, result.output
    assert 'no checklist items found' in result.output.lower()
