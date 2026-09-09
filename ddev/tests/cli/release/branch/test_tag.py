# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import base64
import json
from unittest.mock import call as c

import httpx
import pytest
from httpx import HTTPStatusError, Request, Response

from ddev.cli.release.branch.tag import _open_datadog_agent_bump_pr as REAL_OPEN_DATADOG_AGENT_BUMP_PR
from ddev.utils.git import GitRepository
from ddev.utils.github_async.models import FileContent, PullRequestSimple
from ddev.utils.github_errors import GitHubAuthenticationError

ORIGIN_REF = 'origin/7.56.x'


def test_tag_check_open_prs_warns_and_allows_continue(ddev, git, mocker, config_file):
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()

    mock_pr = mocker.MagicMock()
    mock_pr.number = 1234
    mock_pr.title = 'Fix thing'
    mock_pr.html_url = 'https://example.invalid/pr/1234'
    list_prs = mocker.patch(
        'ddev.utils.github.GitHubManager.list_open_pull_requests_targeting_base',
        return_value=[mock_pr],
    )

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', input='y\n')

    assert result.exit_code == 0, result.output
    assert git.method_calls[-2:] == [
        c.tag('7.56.0', message='7.56.0', ref=ORIGIN_REF),
        c.push('7.56.0'),
    ]
    assert 'Found 1 open PR(s) targeting base branch 7.56.x' in result.output
    assert '#1234 Fix thing' in result.output
    assert 'Open PRs found targeting 7.56.x' in result.output
    list_prs.assert_called_once_with('7.56.x')


def test_tag_skip_open_pr_check(ddev, git, mocker, config_file):
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()

    list_prs = mocker.patch('ddev.utils.github.GitHubManager.list_open_pull_requests_targeting_base')

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '--skip-open-pr-check', input='y\n')

    _assert_tag_pushed(git, result, '7.56.0')
    list_prs.assert_not_called()


def test_tag_github_api_error_degrades_gracefully(ddev, git, mocker, config_file):
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()

    mocker.patch(
        'ddev.utils.github.GitHubManager.list_open_pull_requests_targeting_base',
        side_effect=Exception('API error'),
    )

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', input='y\n')

    _assert_tag_pushed(git, result, '7.56.0')
    assert 'unable to check for open PRs' in result.output


def test_tag_open_pr_authentication_failure_aborts_before_tagging(ddev, git, mocker, config_file):
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()
    request = Request('GET', 'https://api.github.com/search/issues')
    error = HTTPStatusError('forbidden', request=request, response=Response(403, request=request))
    mocker.patch(
        'ddev.utils.github.GitHubManager.list_open_pull_requests_targeting_base',
        side_effect=GitHubAuthenticationError.from_http_status_error(error),
    )

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', input='y\n')

    assert result.exit_code == 1, result.output
    assert 'ddev config set github.token' in result.output
    assert 'unable to check for open PRs' not in result.output
    git.tag.assert_not_called()
    git.push.assert_not_called()


NO_CONFIRMATION_SO_ABORT = 'Did not get confirmation, aborting. Did not create or push the tag.'
RC_NUMBER_PROMPT = 'What RC number are we tagging? (hit ENTER to accept suggestion) [{}]'
TAG_THIS_RELEASE_PROMPT = 'You are on release branch `7.56.x`. Tag this release?'
LS_REMOTE_OK = 'abc123\trefs/heads/7.56.x\n'
RESOLVED_COMMIT_SHA = '1111111111111111111111111111111111111111'

EXAMPLE_TAGS = [
    '7.56.0-rc.1',
    # Random RC tag from DBM. We should make sure we ignore it.
    '7.56.0-rc.1-dbm-agent-jobs',
    # Including RC 11 is interesting because it makes sure we parse the versions before we sort them.
    # The naive sort will think RC 11 is earlier than RC 2.
    '7.56.0-rc.11',
    '7.56.0-rc.2',
    # Skipping RCs, we go from 2 to 5.
    '7.56.0-rc.5',
    '7.56.0-rc.6',
    '7.56.0-rc.7',
    '7.56.0-rc.8',
]


def _capture_dispatch(*args):
    """Dispatch `git.capture(...)` mock calls by their first argument.

    Tests can override individual subcommands by replacing `git.capture.side_effect` outright.
    Defaulting to a per-subcommand mapping (instead of one global return_value) keeps unrelated
    tests from silently masking new code paths.
    """
    if not args:
        return ''
    sub = args[0]
    if sub == 'ls-remote':
        return LS_REMOTE_OK
    if sub == 'rev-parse':
        return f'{RESOLVED_COMMIT_SHA}\n'
    return ''


@pytest.fixture
def basic_git(mocker):
    mock_git = mocker.create_autospec(GitRepository)
    # We're patching the creation of the GitRepository class.
    # That's why we need a function that returns the mock.
    mocker.patch('ddev.repo.core.GitRepository', lambda _: mock_git)
    mock_git.capture.side_effect = _capture_dispatch
    # Default tagging tests off the datadog-agent PR flow, which has its own dedicated tests. The
    # `agent_pr_git` fixture restores the real implementation for those.
    mocker.patch('ddev.cli.release.branch.tag._open_datadog_agent_bump_pr')
    return mock_git


@pytest.fixture
def git(basic_git, mocker):
    mocker.patch('ddev.cli.release.branch.tag._build_agent_yaml_points_to_main', return_value=False)
    basic_git.current_branch.return_value = '7.56.x'
    basic_git.tags.return_value = EXAMPLE_TAGS[:]
    return basic_git


def _assert_tag_pushed(git, result, tag, ref=ORIGIN_REF):
    assert result.exit_code == 0, result.output
    assert git.method_calls[-2:] == [
        c.tag(tag, message=tag, ref=ref),
        c.push(tag),
    ]
    expected_prompt = f'Create and push this tag: {tag}?'
    assert expected_prompt in result.output


def test_wrong_branch_no_release_aborts(ddev, basic_git):
    """
    With no --release and not on a release branch, the command aborts and asks for --release.
    """
    name = 'foo'
    basic_git.current_branch.return_value = name

    result = ddev('release', 'branch', 'tag')

    assert result.exit_code == 1, result.output
    assert 'is not a release branch' in result.output
    assert '--release' in result.output


def test_invalid_release_value_aborts(ddev, git):
    result = ddev('release', 'branch', 'tag', '--release', 'not-a-release')
    assert result.exit_code != 0, result.output
    assert 'Invalid `--release` value' in result.output


@pytest.mark.parametrize(
    'release_input',
    [
        pytest.param('7.56', id='major.minor'),
        pytest.param('7.56.x', id='major.minor.x'),
    ],
)
def test_release_input_normalized(ddev, git, release_input):
    """
    `--release` accepts both `7.56` and `7.56.x` and normalizes to `7.56.x`.
    """
    result = ddev('release', 'branch', 'tag', '--release', release_input, '--final', input='y\n')

    _assert_tag_pushed(git, result, '7.56.0')


def test_release_branch_not_on_origin_aborts(ddev, git):
    """
    If the release branch is missing from origin, the command aborts.
    """
    git.capture.side_effect = lambda *args: ''
    result = ddev('release', 'branch', 'tag', '--release', '7.99.x', '--final', input='y\n')

    assert result.exit_code == 1, result.output
    assert 'does not exist on `origin`' in result.output


def test_confirm_release_branch_when_no_release_arg(ddev, git):
    """
    With no --release and already on a release branch, we ask to confirm before tagging.
    """
    result = ddev('release', 'branch', 'tag', '--final', input='y\ny\n')

    _assert_tag_pushed(git, result, '7.56.0')
    assert TAG_THIS_RELEASE_PROMPT in result.output


def test_decline_release_branch_when_no_release_arg(ddev, git):
    result = ddev('release', 'branch', 'tag', '--final', input='n\n')
    assert result.exit_code == 1, result.output
    assert TAG_THIS_RELEASE_PROMPT in result.output
    assert NO_CONFIRMATION_SO_ABORT in result.output


def test_middle_of_release_next_rc(ddev, git):
    """
    We're in the middle of a release, some RCs are already done. We want to create the next RC.
    """
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', input='\ny\n')

    _assert_tag_pushed(git, result, '7.56.0-rc.12')
    assert RC_NUMBER_PROMPT.format('12') in result.output


@pytest.mark.parametrize(
    'no_confirm',
    [
        pytest.param('n', id='explicit abort'),
        pytest.param('', id='abort by default'),
        pytest.param('x', id='abort on any other input'),
    ],
)
@pytest.mark.parametrize('rc_num', ['3', '10'])
@pytest.mark.parametrize('last_rc', [11, 12])
def test_do_not_confirm_non_sequential_rc(ddev, git, rc_num, no_confirm, last_rc):
    """
    Reject the warning when going backwards in RC numbers.
    """
    git.tags.return_value.append(f'7.56.0-rc.{last_rc}')
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', input=f'{rc_num}\n{no_confirm}\n')

    assert RC_NUMBER_PROMPT.format(str(last_rc + 1)) in result.output
    assert (
        '!!! WARNING !!!\n'
        f'The latest RC is {last_rc}. You are about to go back in time by creating an RC with a number less than that. '
        'Are you sure? [y/N]'
    ) in result.output
    assert result.exit_code == 1, result.output
    assert NO_CONFIRMATION_SO_ABORT in result.output


@pytest.mark.parametrize('rc_num', ['3', '10'])
def test_confirm_non_sequential_rc(ddev, git, rc_num):
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', input=f'{rc_num}\ny\ny\n')

    assert RC_NUMBER_PROMPT.format('12') in result.output
    assert (
        '!!! WARNING !!!\n'
        'The latest RC is 11. You are about to go back in time by creating an RC with a number less than that. '
        'Are you sure? [y/N]'
    ) in result.output
    _assert_tag_pushed(git, result, f'7.56.0-rc.{rc_num}')


@pytest.mark.parametrize('rc_num', ['1', '5', '11'])
def test_existing_rc_tag_re_runs_follow_up_without_re_tagging(ddev, git, mocker, rc_num):
    """Re-running for an existing RC tag is idempotent: no re-tag, but the follow-up steps run again.

    This is the recovery path for when the datadog-agent release branch did not exist at tag time,
    so the bump PR could not be opened until later.
    """
    open_pr = mocker.patch('ddev.cli.release.branch.tag._open_datadog_agent_bump_pr')
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', input=f'{rc_num}\n')

    assert result.exit_code == 0, result.output
    assert RC_NUMBER_PROMPT.format('12') in result.output
    assert f'Tag 7.56.0-rc.{rc_num} already exists; skipping tag creation' in result.output
    git.tag.assert_not_called()
    git.push.assert_not_called()
    # The bump PR is (re)opened, pinning the commit the existing tag points at (its last argument).
    open_pr.assert_called_once()
    assert open_pr.call_args.args[-1] == f'7.56.0-rc.{rc_num}'


def test_existing_final_tag_re_runs_follow_up_without_re_tagging(ddev, git, mocker):
    """`--final N` selects an existing final tag so its follow-up steps can be re-run."""
    git.tags.return_value = ['7.56.0']
    open_pr = mocker.patch('ddev.cli.release.branch.tag._open_datadog_agent_bump_pr')

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '0', '--yes')

    assert result.exit_code == 0, result.output
    assert 'Tag 7.56.0 already exists; skipping tag creation' in result.output
    git.tag.assert_not_called()
    git.push.assert_not_called()
    open_pr.assert_called_once()
    assert open_pr.call_args.args[-2:] == ('7.56.0', '7.56.0')


def test_abort_if_tag_less_than_one(ddev, git):
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', input='0\ny\n')

    assert RC_NUMBER_PROMPT.format('12') in result.output
    assert result.exit_code == 1, result.output
    assert 'RC number must be at least 1.' in result.output


@pytest.mark.parametrize(
    'no_confirm',
    [
        pytest.param('n', id='explicit abort'),
        pytest.param('', id='abort by default'),
        pytest.param('x', id='abort on any other input'),
    ],
)
def test_abort_valid_rc(ddev, git, no_confirm):
    git.tags.return_value = []
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', input=f'\n{no_confirm}\n')

    assert RC_NUMBER_PROMPT.format('1') in result.output
    assert result.exit_code == 1, result.output
    assert NO_CONFIRMATION_SO_ABORT in result.output


@pytest.mark.parametrize(
    'rc_num_input, rc_num',
    [
        pytest.param('', '1', id='implicit sequential'),
        pytest.param('2', '2', id='explicit non-sequential'),
    ],
)
@pytest.mark.parametrize('tags, patch', [([], '0'), (EXAMPLE_TAGS + ['7.56.0'], '1')])
def test_first_rc(ddev, git, rc_num_input, rc_num, tags, patch):
    """
    First RC for a new release.
    """
    git.tags.return_value = tags
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', input=f'{rc_num_input}\ny\n')

    _assert_tag_pushed(git, result, f'7.56.{patch}-rc.{rc_num}')
    assert RC_NUMBER_PROMPT.format('1') in result.output


@pytest.mark.parametrize(
    'latest_final_tag, expected_new_final_tag',
    [
        pytest.param('', '7.56.0', id='no final tag yet'),
        pytest.param('7.56.0', '7.56.1', id='final tag present, so we are making a bugfix release'),
    ],
)
def test_final(ddev, git, latest_final_tag, expected_new_final_tag):
    git.tags.return_value.append(latest_final_tag)
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', input='y\n')

    _assert_tag_pushed(git, result, expected_new_final_tag)


def test_final_with_explicit_patch(ddev, git):
    """`--final N` tags patch N explicitly instead of the next patch version."""
    git.tags.return_value.append('7.56.0')

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '2', '--yes')

    _assert_tag_pushed(git, result, '7.56.2')


@pytest.mark.parametrize('final_arg', ['--final=banana', '--final=1.5'])
def test_final_invalid_value_aborts(ddev, git, final_arg):
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', final_arg)
    assert result.exit_code != 0, result.output
    assert '`--final` value must be a non-negative integer' in result.output


def test_rc_with_explicit_value(ddev, git):
    """
    `--rc N` pins the RC number without prompting.
    """
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--rc', '12', input='y\n')
    _assert_tag_pushed(git, result, '7.56.0-rc.12')
    assert RC_NUMBER_PROMPT.format('12') not in result.output


def test_rc_explicit_value_skips_ahead_warns(ddev, git):
    """
    `--rc N` with N > expected_next emits a gap warning but proceeds.
    """
    # Last RC is 11 (per EXAMPLE_TAGS), so expected next is 12. Skipping to 15.
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--rc', '15', input='y\n')

    _assert_tag_pushed(git, result, '7.56.0-rc.15')
    assert 'skips ahead' in result.output
    assert 'Missing RC number(s): 12, 13, 14' in result.output
    assert '--rc 12 --ref' in result.output


def test_rc_explicit_value_no_gap_no_warning(ddev, git):
    """
    `--rc N` matching the expected next number does not emit a gap warning.
    """
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--rc', '12', input='y\n')
    _assert_tag_pushed(git, result, '7.56.0-rc.12')
    assert 'skips ahead' not in result.output


@pytest.mark.parametrize('rc_arg', ['--rc=banana', '--rc=0'])
def test_rc_invalid_value_aborts(ddev, git, rc_arg):
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', rc_arg)
    assert result.exit_code != 0, result.output
    assert '`--rc` value must be a positive integer' in result.output


def test_final_and_rc_mutually_exclusive(ddev, git):
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '--rc', '3')
    assert result.exit_code != 0, result.output
    assert 'mutually exclusive' in result.output


def test_yes_skips_all_confirmations(ddev, git):
    """
    `--yes` skips both the "tag this release?" prompt and the final confirm.
    Also skips the RC-number prompt by using the suggested value.
    """
    result = ddev('release', 'branch', 'tag', '--yes')
    _assert_tag_pushed(git, result, '7.56.0-rc.12')
    assert RC_NUMBER_PROMPT.format('12') not in result.output
    assert 'auto-yes' in result.output
    assert 'Using auto-suggested RC number: 12' in result.output


def test_yes_with_pinned_rc(ddev, git):
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--rc', '20', '--yes')
    _assert_tag_pushed(git, result, '7.56.0-rc.20')
    assert 'skips ahead' in result.output


def _make_ref_dispatcher(rev_parse=None, is_ancestor=None):
    """Build a `capture` side_effect that dispatches by subcommand for --ref tests.

    Delegates to `_capture_dispatch` for any subcommand it doesn't explicitly handle so the
    default `ls-remote` payload stays defined in exactly one place.
    """

    def dispatch(*args):
        sub = args[0] if args else ''
        if sub == 'rev-parse':
            if isinstance(rev_parse, BaseException):
                raise rev_parse
            return rev_parse
        if sub == 'merge-base':
            if isinstance(is_ancestor, BaseException):
                raise is_ancestor
            return is_ancestor
        return _capture_dispatch(*args)

    return dispatch


def test_ref_validates_and_tags_at_commit(ddev, git):
    """
    `--ref <commit>` tags that commit instead of the branch tip.
    """
    git.capture.side_effect = _make_ref_dispatcher(rev_parse='cafef00d\n', is_ancestor='')
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '--ref', 'cafef00d', input='y\n')

    assert result.exit_code == 0, result.output
    assert 'at cafef00d?' in result.output
    assert git.method_calls[-2:] == [
        c.tag('7.56.0', message='7.56.0', ref='cafef00d'),
        c.push('7.56.0'),
    ]


def test_ref_does_not_resolve_aborts(ddev, git):
    git.capture.side_effect = _make_ref_dispatcher(rev_parse=OSError('bad ref'))
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '--ref', 'nope', input='y\n')
    assert result.exit_code == 1, result.output
    assert 'does not resolve to a commit' in result.output


def test_ref_not_ancestor_aborts(ddev, git):
    git.capture.side_effect = _make_ref_dispatcher(rev_parse='badf00d\n', is_ancestor=OSError('not ancestor'))
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '--ref', 'badf00d', input='y\n')
    assert result.exit_code == 1, result.output
    assert 'is not an ancestor of' in result.output


def test_no_worktree_subprocess_invoked(ddev, git):
    """
    The command must never touch `git worktree`. Previously it created a worktree to check out
    `origin/<branch>` for tagging; now it operates against the ref directly. Worktree ops can
    go through either `run` (add/remove) or `capture` (list), so both are filtered.
    """
    git.current_branch.return_value = 'master'
    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', input='y\n')

    assert result.exit_code == 0, result.output
    worktree_calls = [
        call for call in git.method_calls if call[0] in ('run', 'capture') and call.args and call.args[0] == 'worktree'
    ]
    assert worktree_calls == []


def test_local_release_branch_not_pulled(ddev, git):
    """
    The command must never pull the user's local release branch. Tagging operates against
    `origin/<branch>` only, so the user's local checkout state is irrelevant.
    """
    ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', input='y\n')
    git.pull.assert_not_called()


def test_build_agent_yaml_already_updated_does_not_dispatch_workflow(ddev, git, mocker):
    dispatch_workflow = mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow')

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '--skip-open-pr-check', input='y\n')

    _assert_tag_pushed(git, result, '7.56.0')
    dispatch_workflow.assert_not_called()


def test_build_agent_yaml_points_to_main_warns_and_continues(ddev, basic_git, mocker):
    basic_git.current_branch.return_value = '7.56.x'
    basic_git.tags.return_value = []
    mocker.patch('ddev.cli.release.branch.tag._build_agent_yaml_points_to_main', return_value=True)
    dispatch_workflow = mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow')

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--skip-open-pr-check', input='\ny\n')

    assert result.exit_code == 0, result.output
    assert '`.gitlab/build_agent.yaml` still points to `main`' in result.output
    assert 'Dispatched `update-build-agent-yaml.yml`' in result.output
    assert 'Tagging will continue.' in result.output
    dispatch_workflow.assert_called_once_with('update-build-agent-yaml.yml', 'master', {'branch': '7.56.x'})
    basic_git.tag.assert_called_once_with('7.56.0-rc.1', message='7.56.0-rc.1', ref=ORIGIN_REF)
    basic_git.push.assert_called_once_with('7.56.0-rc.1')


def test_build_agent_yaml_workflow_dispatch_waits_for_tag_confirmation(ddev, basic_git, mocker):
    basic_git.current_branch.return_value = '7.56.x'
    basic_git.tags.return_value = []
    mocker.patch('ddev.cli.release.branch.tag._build_agent_yaml_points_to_main', return_value=True)
    dispatch_workflow = mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow')

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '--skip-open-pr-check', input='n\n')

    assert result.exit_code == 1, result.output
    assert NO_CONFIRMATION_SO_ABORT in result.output
    dispatch_workflow.assert_not_called()
    basic_git.push.assert_not_called()


def test_build_agent_yaml_workflow_dispatch_failure_warns_and_continues(ddev, basic_git, mocker):
    basic_git.current_branch.return_value = '7.56.x'
    basic_git.tags.return_value = []
    mocker.patch('ddev.cli.release.branch.tag._build_agent_yaml_points_to_main', return_value=True)
    dispatch_workflow = mocker.patch(
        'ddev.utils.github.GitHubManager.dispatch_workflow',
        side_effect=HTTPStatusError(
            'API error', request=Request('POST', 'https://api.github.com'), response=Response(500)
        ),
    )

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '--skip-open-pr-check', input='y\n')

    assert result.exit_code == 0, result.output
    assert 'Warning: unable to trigger `update-build-agent-yaml.yml`: API error' in result.output
    assert 'gh workflow run update-build-agent-yaml.yml -f branch=7.56.x' in result.output
    assert 'Dispatched `update-build-agent-yaml.yml`' not in result.output
    dispatch_workflow.assert_called_once_with('update-build-agent-yaml.yml', 'master', {'branch': '7.56.x'})
    basic_git.tag.assert_called_once_with('7.56.0', message='7.56.0', ref=ORIGIN_REF)
    basic_git.push.assert_called_once_with('7.56.0')


def test_build_agent_yaml_workflow_authentication_failure_uses_central_handler(ddev, basic_git, mocker):
    basic_git.current_branch.return_value = '7.56.x'
    basic_git.tags.return_value = []
    mocker.patch('ddev.cli.release.branch.tag._build_agent_yaml_points_to_main', return_value=True)
    request = Request('POST', 'https://api.github.com')
    response = Response(403, request=request)
    error = HTTPStatusError('forbidden', request=request, response=response)
    mocker.patch(
        'ddev.utils.github.GitHubManager.dispatch_workflow',
        side_effect=GitHubAuthenticationError.from_http_status_error(error),
    )

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '--skip-open-pr-check', input='y\n')

    assert result.exit_code == 1, result.output
    assert 'ddev config set github.token' in result.output
    assert 'gh workflow run update-build-agent-yaml.yml -f branch=7.56.x' in result.output
    basic_git.tag.assert_called_once_with('7.56.0', message='7.56.0', ref=ORIGIN_REF)
    basic_git.push.assert_called_once_with('7.56.0')


AGENT_RELEASE_JSON = (
    '{\n'
    '    "base_branch": "7.56.x",\n'
    '    "current_milestone": "7.56.0",\n'
    '    "dependencies": {\n'
    '        "INTEGRATIONS_CORE_VERSION": "7.56.x",\n'
    '        "JMXFETCH_VERSION": "0.49.5"\n'
    '    },\n'
    '    "last_stable": {\n'
    '        "7": "7.55.0"\n'
    '    }\n'
    '}\n'
)


@pytest.fixture
def agent_pr_git(basic_git, mocker):
    """Like the `git` fixture, but restores `_open_datadog_agent_bump_pr` so it actually runs."""
    mocker.patch('ddev.cli.release.branch.tag._build_agent_yaml_points_to_main', return_value=False)
    mocker.patch('ddev.cli.release.branch.tag._open_datadog_agent_bump_pr', REAL_OPEN_DATADOG_AGENT_BUMP_PR)
    basic_git.current_branch.return_value = '7.56.x'
    basic_git.tags.return_value = EXAMPLE_TAGS[:]
    return basic_git


AGENT_BASE_COMMIT_SHA = 'a' * 40
AGENT_HEAD_BLOB_SHA = 'headblob'


def _release_json_file(release_json, blob_sha):
    return FileContent(
        type='file',
        encoding='base64',
        size=len(release_json),
        name='release.json',
        path='release.json',
        content=base64.b64encode(release_json.encode()).decode(),
        sha=blob_sha,
    )


def _mock_release_json(
    fake_async_github,
    release_json=AGENT_RELEASE_JSON,
    head_branch=None,
    head_release_json=None,
):
    """Register the datadog-agent `release.json` responses the fake serves to the pin-PR flow.

    The base-branch read is matched on `ref=AGENT_BASE_COMMIT_SHA` (the fake's `get_ref` default),
    and `release.json` on the head branch serves `head_release_json` — or a 404 (branch missing)
    when `head_release_json` is None. Registering by ref keeps the base and head snapshots
    distinguishable.
    """
    fake_async_github.mock_response(
        'get_content', _release_json_file(release_json, 'baseblob'), ref=AGENT_BASE_COMMIT_SHA
    )
    if head_branch is None:
        return
    if head_release_json is None:
        fake_async_github.mock_response(
            'get_content',
            httpx.HTTPStatusError(
                'Not Found', request=Request('GET', 'https://api.github.com'), response=Response(404)
            ),
            ref=head_branch,
        )
    else:
        fake_async_github.mock_response(
            'get_content', _release_json_file(head_release_json, AGENT_HEAD_BLOB_SHA), ref=head_branch
        )


def test_agent_pr_first_rc_of_milestone_targets_main(ddev, agent_pr_git, fake_async_github, config_file):
    """`X.Y.0-rc.1` is tagged before the Agent release branch is cut, so the pin goes to `main`."""
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()
    agent_pr_git.tags.return_value = []
    _mock_release_json(fake_async_github, head_branch='integrations-core/bump-7.56.0-rc.1')

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--skip-open-pr-check', input='\ny\n')

    assert result.exit_code == 0, result.output
    agent_pr_git.tag.assert_called_once_with('7.56.0-rc.1', message='7.56.0-rc.1', ref=ORIGIN_REF)
    assert fake_async_github.last_call('get_ref').kwargs['ref'] == 'heads/main'
    # `release.json` is read at the commit SHA `get_ref` returned, not at the moving branch name.
    assert fake_async_github.calls_to('get_content')[0].kwargs['ref'] == AGENT_BASE_COMMIT_SHA
    assert fake_async_github.last_call('create_pull_request').kwargs['base'] == 'main'
    assert 'against `main`' in result.output


def test_agent_pr_later_rc_targets_release_branch(ddev, agent_pr_git, fake_async_github, config_file):
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()
    _mock_release_json(fake_async_github, head_branch='integrations-core/bump-7.56.0-rc.12')

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--skip-open-pr-check', input='\ny\n')

    assert result.exit_code == 0, result.output
    agent_pr_git.tag.assert_called_once_with('7.56.0-rc.12', message='7.56.0-rc.12', ref=ORIGIN_REF)
    assert fake_async_github.calls_to('get_content')[0].kwargs['ref'] == AGENT_BASE_COMMIT_SHA
    assert fake_async_github.last_call('create_pull_request').kwargs['base'] == '7.56.x'


def test_agent_pr_patch_rc1_targets_release_branch(ddev, agent_pr_git, fake_async_github, config_file):
    """Only the first RC of a milestone targets `main`; a patch RC like `7.56.1-rc.1` does not."""
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()
    agent_pr_git.tags.return_value = ['7.56.0']
    _mock_release_json(fake_async_github, head_branch='integrations-core/bump-7.56.1-rc.1')

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--skip-open-pr-check', input='\ny\n')

    assert result.exit_code == 0, result.output
    agent_pr_git.tag.assert_called_once_with('7.56.1-rc.1', message='7.56.1-rc.1', ref=ORIGIN_REF)
    assert fake_async_github.calls_to('get_content')[0].kwargs['ref'] == AGENT_BASE_COMMIT_SHA
    assert fake_async_github.last_call('create_pull_request').kwargs['base'] == '7.56.x'


def test_agent_pr_final_tag_targets_release_branch_and_bumps_pin(ddev, agent_pr_git, fake_async_github, config_file):
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()
    _mock_release_json(fake_async_github, head_branch='integrations-core/bump-7.56.0')

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '--skip-open-pr-check', input='y\n')

    assert result.exit_code == 0, result.output
    assert fake_async_github.last_call('create_pull_request').kwargs['base'] == '7.56.x'
    # The committed release.json pins the integrations-core commit SHA the tag was placed on,
    # not the tag name.
    committed = base64.b64decode(
        fake_async_github.last_call('create_or_update_file_contents').kwargs['content']
    ).decode()
    assert f'"INTEGRATIONS_CORE_VERSION": "{RESOLVED_COMMIT_SHA}"' in committed
    assert 'Datadog-agent bump PR created' in result.output


def test_agent_pr_pins_the_ref_commit_not_the_branch_tip(ddev, agent_pr_git, fake_async_github, config_file):
    """`--ref` tags a non-tip commit; the pin must follow that commit, not the branch tip."""
    ref_commit_sha = 'cafef00d' * 5
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()
    _mock_release_json(fake_async_github, head_branch='integrations-core/bump-7.56.0')

    def dispatch(*args):
        # Give the `--ref` commit a distinct SHA from the branch tip so the test can tell the pin
        # followed the right one.
        if args[:2] == ('rev-parse', '--verify') and 'cafef00d' in args[2]:
            return f'{ref_commit_sha}\n'
        return _capture_dispatch(*args)

    agent_pr_git.capture.side_effect = dispatch

    result = ddev(
        'release',
        'branch',
        'tag',
        '--release',
        '7.56.x',
        '--final',
        '--ref',
        'cafef00d',
        '--skip-open-pr-check',
        input='y\n',
    )

    assert result.exit_code == 0, result.output
    agent_pr_git.tag.assert_called_once_with('7.56.0', message='7.56.0', ref=ref_commit_sha)
    committed = base64.b64decode(
        fake_async_github.last_call('create_or_update_file_contents').kwargs['content']
    ).decode()
    assert f'"INTEGRATIONS_CORE_VERSION": "{ref_commit_sha}"' in committed


def test_agent_pr_skipped_when_pin_already_matches(ddev, agent_pr_git, fake_async_github, config_file):
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()
    already_pinned = AGENT_RELEASE_JSON.replace(
        '"INTEGRATIONS_CORE_VERSION": "7.56.x"', f'"INTEGRATIONS_CORE_VERSION": "{RESOLVED_COMMIT_SHA}"'
    )
    _mock_release_json(fake_async_github, release_json=already_pinned)

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '--skip-open-pr-check', input='y\n')

    assert result.exit_code == 0, result.output
    # Already pinned: no branch is cut, no commit is made, no PR is opened.
    fake_async_github.assert_not_called('create_or_update_file_contents')
    fake_async_github.assert_not_called('create_pull_request')
    assert f'already pins `{RESOLVED_COMMIT_SHA}`' in result.output


def test_agent_pr_api_failure_does_not_fail_the_pushed_tag(ddev, agent_pr_git, fake_async_github, config_file):
    """The tag is already pushed when the PR is attempted, so a PR API error must only warn."""
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()
    _mock_release_json(fake_async_github, head_branch='integrations-core/bump-7.56.0')
    fake_async_github.mock_response(
        'create_pull_request',
        httpx.HTTPStatusError('boom', request=Request('POST', 'https://api.github.com'), response=Response(500)),
    )

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '--skip-open-pr-check', input='y\n')

    assert result.exit_code == 0, result.output
    agent_pr_git.tag.assert_called_once_with('7.56.0', message='7.56.0', ref=ORIGIN_REF)
    agent_pr_git.push.assert_called_once_with('7.56.0')
    assert 'could not be created' in result.output


def test_agent_pr_reports_when_release_branch_missing_on_agent(ddev, agent_pr_git, fake_async_github, config_file):
    """A 404 resolving the base branch means the Agent release branch isn't cut yet, not a bug."""
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()
    fake_async_github.mock_response(
        'get_ref',
        httpx.HTTPStatusError('Not Found', request=Request('GET', 'https://api.github.com'), response=Response(404)),
    )

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--final', '--skip-open-pr-check', input='y\n')

    assert result.exit_code == 0, result.output
    agent_pr_git.tag.assert_called_once_with('7.56.0', message='7.56.0', ref=ORIGIN_REF)
    assert 'the `7.56.x` branch does not exist on datadog-agent yet' in result.output


def test_agent_pr_reports_existing_open_pr_on_rerun(ddev, agent_pr_git, fake_async_github, config_file):
    """A rerun while the first run's PR is still open reports it instead of recreating it."""
    existing_pr_url = 'https://github.com/DataDog/datadog-agent/pull/7'
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()
    _mock_release_json(fake_async_github)
    fake_async_github.mock_response(
        'list_pull_requests',
        [PullRequestSimple(number=7, html_url=existing_pr_url)],
    )

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--rc', '11', '--yes')

    assert result.exit_code == 0, result.output
    assert 'Tag 7.56.0-rc.11 already exists; skipping tag creation' in result.output
    assert (
        fake_async_github.last_call('list_pull_requests').kwargs['head']
        == 'DataDog:integrations-core/bump-7.56.0-rc.11'
    )
    fake_async_github.assert_not_called('create_ref')
    fake_async_github.assert_not_called('create_or_update_file_contents')
    fake_async_github.assert_not_called('create_pull_request')
    assert f'Datadog-agent bump PR already open: {existing_pr_url}' in result.output


def test_agent_pr_reuses_head_branch_left_by_failed_run(ddev, agent_pr_git, fake_async_github, config_file):
    """A head branch from a partially failed run is reused and updated, not re-created (HTTP 422)."""
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()
    _mock_release_json(
        fake_async_github,
        head_branch='integrations-core/bump-7.56.0-rc.11',
        # The head branch was cut but the file commit never happened, so it still carries the
        # base content — but its own blob SHA.
        head_release_json=AGENT_RELEASE_JSON,
    )

    result = ddev('release', 'branch', 'tag', '--release', '7.56.x', '--rc', '11', '--yes')

    assert result.exit_code == 0, result.output
    assert 'Tag 7.56.0-rc.11 already exists; skipping tag creation' in result.output
    fake_async_github.assert_not_called('create_ref')
    update = fake_async_github.last_call('create_or_update_file_contents')
    assert update.kwargs['branch'] == 'integrations-core/bump-7.56.0-rc.11'
    assert update.kwargs['sha'] == AGENT_HEAD_BLOB_SHA
    committed = base64.b64decode(update.kwargs['content']).decode()
    assert f'"INTEGRATIONS_CORE_VERSION": "{RESOLVED_COMMIT_SHA}"' in committed
    assert 'Datadog-agent bump PR created' in result.output


def test_bump_integrations_core_version_preserves_other_keys():
    from ddev.cli.release.branch.tag import _bump_integrations_core_version

    result = _bump_integrations_core_version(AGENT_RELEASE_JSON, RESOLVED_COMMIT_SHA)

    data = json.loads(result)
    assert data['dependencies']['INTEGRATIONS_CORE_VERSION'] == RESOLVED_COMMIT_SHA
    assert data['dependencies']['JMXFETCH_VERSION'] == '0.49.5'
    assert data['current_milestone'] == '7.56.0'
    assert result.endswith('\n')
