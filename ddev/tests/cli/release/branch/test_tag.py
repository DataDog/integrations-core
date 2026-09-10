# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import base64
import json
from unittest.mock import call as c

import pytest
from httpx import HTTPStatusError, Request, Response

from ddev.cli.release.branch.tag import _bump_integrations_core_version
from ddev.cli.release.branch.tag import _open_datadog_agent_bump_pr as REAL_OPEN_DATADOG_AGENT_BUMP_PR
from ddev.utils.git import GitRepository
from ddev.utils.github_async.models import FileContent, PullRequest
from ddev.utils.github_errors import GitHubAuthenticationError

ORIGIN_REF = 'origin/7.56.x'

NO_CONFIRMATION_SO_ABORT = 'Did not get confirmation, aborting. Did not create or push the tag.'
RC_NUMBER_PROMPT = 'What RC number are we tagging? (hit ENTER to accept suggestion) [{}]'
TAG_THIS_RELEASE_PROMPT = 'You are on release branch `7.56.x`. Tag this release?'
BACKWARD_RC_WARNING = (
    '!!! WARNING !!!\n'
    'The latest RC is {}. '
    'You are about to go back in time by creating an RC with a number less than that. '
    'Are you sure? [y/N]'
)
NO_CONFIRM_INPUTS = [
    pytest.param('n', id='explicit abort'),
    pytest.param('', id='abort by default'),
    pytest.param('x', id='abort on any other input'),
]
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


def _http_status_error(status_code, message='boom', method='GET'):
    """An `httpx.HTTPStatusError` shaped like the ones the GitHub client raises."""
    request = Request(method, 'https://api.github.com')
    return HTTPStatusError(message, request=request, response=Response(status_code, request=request))


def _run_tag(ddev, *args, input=None):
    """Invoke `ddev release branch tag --release 7.56.x` with extra args."""
    return ddev('release', 'branch', 'tag', '--release', '7.56.x', *args, input=input)


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


@pytest.fixture
def github_credentials(config_file):
    config_file.model.github = {'user': 'test-user', 'token': 'test-token'}
    config_file.save()


@pytest.fixture
def basic_git(mocker):
    mock_git = mocker.create_autospec(GitRepository)
    # We're patching the creation of the GitRepository class.
    # That's why we need a function that returns the mock.
    mocker.patch('ddev.repo.core.GitRepository', lambda _: mock_git)
    mock_git.capture.side_effect = _capture_dispatch
    # Default tagging tests off the datadog-agent PR flow, which has its own dedicated tests. The
    # `agent_pr` fixture restores the real implementation for those.
    mocker.patch('ddev.cli.release.branch.tag._open_datadog_agent_bump_pr')
    return mock_git


@pytest.fixture
def git(basic_git, mocker):
    mocker.patch('ddev.cli.release.branch.tag._build_agent_yaml_points_to_main', return_value=False)
    basic_git.current_branch.return_value = '7.56.x'
    basic_git.tags.return_value = EXAMPLE_TAGS[:]
    return basic_git


@pytest.fixture
def stale_build_agent_yaml(basic_git, mocker):
    """Release branch state where `.gitlab/build_agent.yaml` still points to `main`."""
    basic_git.current_branch.return_value = '7.56.x'
    basic_git.tags.return_value = []
    mocker.patch('ddev.cli.release.branch.tag._build_agent_yaml_points_to_main', return_value=True)
    return basic_git


def _assert_tag_pushed(git, result, tag, ref=ORIGIN_REF):
    assert result.exit_code == 0, result.output
    assert git.method_calls.count(c.tag(tag, message=tag, ref=ref)) == 1
    assert git.method_calls.count(c.push(tag)) == 1
    expected_prompt = f'Create and push this tag: {tag}?'
    assert expected_prompt in result.output


def test_tag_check_open_prs_warns_and_allows_continue(ddev, git, mocker, github_credentials):
    mock_pr = mocker.MagicMock()
    mock_pr.number = 1234
    mock_pr.title = 'Fix thing'
    mock_pr.html_url = 'https://example.invalid/pr/1234'
    list_prs = mocker.patch(
        'ddev.utils.github.GitHubManager.list_open_pull_requests_targeting_base',
        return_value=[mock_pr],
    )

    result = _run_tag(ddev, '--final', input='y\n')

    assert 'Found 1 open PR(s) targeting base branch 7.56.x' in result.output
    assert '#1234 Fix thing' in result.output
    assert 'Open PRs found targeting 7.56.x' in result.output
    assert 'Open PRs found targeting 7.56.x. Create and push this tag anyway: 7.56.0?' in result.output
    list_prs.assert_called_once_with('7.56.x')
    assert git.method_calls.count(c.tag('7.56.0', message='7.56.0', ref=ORIGIN_REF)) == 1
    assert git.method_calls.count(c.push('7.56.0')) == 1


def test_tag_skip_open_pr_check(ddev, git, mocker, github_credentials):
    list_prs = mocker.patch('ddev.utils.github.GitHubManager.list_open_pull_requests_targeting_base')

    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    _assert_tag_pushed(git, result, '7.56.0')
    list_prs.assert_not_called()


def test_tag_github_api_error_degrades_gracefully(ddev, git, mocker, github_credentials):
    mocker.patch(
        'ddev.utils.github.GitHubManager.list_open_pull_requests_targeting_base',
        side_effect=Exception('API error'),
    )

    result = _run_tag(ddev, '--final', input='y\n')

    _assert_tag_pushed(git, result, '7.56.0')
    assert 'unable to check for open PRs' in result.output


def test_tag_open_pr_authentication_failure_aborts_before_tagging(ddev, git, mocker, github_credentials):
    error = GitHubAuthenticationError.from_http_status_error(_http_status_error(403, 'forbidden'))
    mocker.patch(
        'ddev.utils.github.GitHubManager.list_open_pull_requests_targeting_base',
        side_effect=error,
    )

    result = _run_tag(ddev, '--final', input='y\n')

    assert result.exit_code == 1, result.output
    assert 'ddev config set github.token' in result.output
    assert 'unable to check for open PRs' not in result.output
    git.tag.assert_not_called()
    git.push.assert_not_called()


def test_wrong_branch_no_release_aborts(ddev, basic_git):
    """
    With no --release and not on a release branch, the command aborts and asks for --release.
    """
    basic_git.current_branch.return_value = 'foo'

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
    result = _run_tag(ddev, input='\ny\n')

    _assert_tag_pushed(git, result, '7.56.0-rc.12')
    assert RC_NUMBER_PROMPT.format('12') in result.output


@pytest.mark.parametrize('no_confirm', NO_CONFIRM_INPUTS)
@pytest.mark.parametrize('rc_num', ['3', '10'])
@pytest.mark.parametrize('last_rc', [11, 12])
def test_do_not_confirm_non_sequential_rc(ddev, git, rc_num, no_confirm, last_rc):
    """
    Reject the warning when going backwards in RC numbers.
    """
    git.tags.return_value.append(f'7.56.0-rc.{last_rc}')
    result = _run_tag(ddev, input=f'{rc_num}\n{no_confirm}\n')

    assert RC_NUMBER_PROMPT.format(str(last_rc + 1)) in result.output
    assert BACKWARD_RC_WARNING.format(last_rc) in result.output
    assert result.exit_code == 1, result.output
    assert NO_CONFIRMATION_SO_ABORT in result.output


@pytest.mark.parametrize('rc_num', ['3', '10'])
def test_confirm_non_sequential_rc(ddev, git, rc_num):
    result = _run_tag(ddev, input=f'{rc_num}\ny\ny\n')

    assert RC_NUMBER_PROMPT.format('12') in result.output
    assert BACKWARD_RC_WARNING.format(11) in result.output
    _assert_tag_pushed(git, result, f'7.56.0-rc.{rc_num}')


def test_existing_rc_tag_aborts(ddev, git):
    """An already-pushed RC tag must not be created again; overwriting is a deliberate git job."""
    result = _run_tag(ddev, '--rc', '1', '--yes')

    assert result.exit_code == 1, result.output
    assert 'Tag 7.56.0-rc.1 already exists. Switch to git to overwrite it.' in result.output
    git.tag.assert_not_called()
    git.push.assert_not_called()


def test_abort_if_tag_less_than_one(ddev, git):
    result = _run_tag(ddev, input='0\ny\n')

    assert RC_NUMBER_PROMPT.format('12') in result.output
    assert result.exit_code == 1, result.output
    assert 'RC number must be at least 1.' in result.output


@pytest.mark.parametrize('no_confirm', NO_CONFIRM_INPUTS)
def test_abort_valid_rc(ddev, git, no_confirm):
    git.tags.return_value = []
    result = _run_tag(ddev, input=f'\n{no_confirm}\n')

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
    result = _run_tag(ddev, input=f'{rc_num_input}\ny\n')

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
    result = _run_tag(ddev, '--final', input='y\n')

    _assert_tag_pushed(git, result, expected_new_final_tag)


def test_rc_with_explicit_value(ddev, git):
    """
    `--rc N` pins the RC number without prompting.
    """
    result = _run_tag(ddev, '--rc', '12', input='y\n')
    _assert_tag_pushed(git, result, '7.56.0-rc.12')
    assert RC_NUMBER_PROMPT.format('12') not in result.output


def test_rc_explicit_value_skips_ahead_warns(ddev, git):
    """
    `--rc N` with N > expected_next emits a gap warning but proceeds.
    """
    # Last RC is 11 (per EXAMPLE_TAGS), so expected next is 12. Skipping to 15.
    result = _run_tag(ddev, '--rc', '15', input='y\n')

    _assert_tag_pushed(git, result, '7.56.0-rc.15')
    assert 'skips ahead' in result.output
    assert 'Missing RC number(s): 12, 13, 14' in result.output
    assert '--rc 12 --ref' in result.output


def test_rc_explicit_value_no_gap_no_warning(ddev, git):
    """
    `--rc N` matching the expected next number does not emit a gap warning.
    """
    result = _run_tag(ddev, '--rc', '12', input='y\n')
    _assert_tag_pushed(git, result, '7.56.0-rc.12')
    assert 'skips ahead' not in result.output


@pytest.mark.parametrize('rc_arg', ['--rc=banana', '--rc=0'])
def test_rc_invalid_value_aborts(ddev, git, rc_arg):
    result = _run_tag(ddev, rc_arg)
    assert result.exit_code != 0, result.output
    assert '`--rc` value must be a positive integer' in result.output


def test_final_and_rc_mutually_exclusive(ddev, git):
    result = _run_tag(ddev, '--final', '--rc', '3')
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
    result = _run_tag(ddev, '--rc', '20', '--yes')
    _assert_tag_pushed(git, result, '7.56.0-rc.20')
    assert 'skips ahead' in result.output


def test_ref_validates_and_tags_at_commit(ddev, git):
    """
    `--ref <commit>` tags that commit instead of the branch tip.
    """
    git.capture.side_effect = _make_ref_dispatcher(rev_parse='cafef00d\n', is_ancestor='')
    result = _run_tag(ddev, '--final', '--ref', 'cafef00d', input='y\n')

    assert result.exit_code == 0, result.output
    assert 'at cafef00d?' in result.output
    assert git.method_calls[-2:] == [
        c.tag('7.56.0', message='7.56.0', ref='cafef00d'),
        c.push('7.56.0'),
    ]


def test_ref_does_not_resolve_aborts(ddev, git):
    git.capture.side_effect = _make_ref_dispatcher(rev_parse=OSError('bad ref'))
    result = _run_tag(ddev, '--final', '--ref', 'nope', input='y\n')
    assert result.exit_code == 1, result.output
    assert 'does not resolve to a commit' in result.output


def test_ref_not_ancestor_aborts(ddev, git):
    git.capture.side_effect = _make_ref_dispatcher(rev_parse='badf00d\n', is_ancestor=OSError('not ancestor'))
    result = _run_tag(ddev, '--final', '--ref', 'badf00d', input='y\n')
    assert result.exit_code == 1, result.output
    assert 'is not an ancestor of' in result.output


def test_no_worktree_subprocess_invoked(ddev, git):
    """
    The command must never touch `git worktree`. Previously it created a worktree to check out
    `origin/<branch>` for tagging; now it operates against the ref directly. Worktree ops can
    go through either `run` (add/remove) or `capture` (list), so both are filtered.
    """
    git.current_branch.return_value = 'master'
    result = _run_tag(ddev, '--final', input='y\n')

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
    _run_tag(ddev, '--final', input='y\n')
    git.pull.assert_not_called()


def test_build_agent_yaml_already_updated_does_not_dispatch_workflow(ddev, git, mocker):
    dispatch_workflow = mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow')

    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    _assert_tag_pushed(git, result, '7.56.0')
    dispatch_workflow.assert_not_called()


def test_build_agent_yaml_points_to_main_warns_and_continues(ddev, stale_build_agent_yaml, mocker):
    dispatch_workflow = mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow')

    result = _run_tag(ddev, '--skip-open-pr-check', input='\ny\n')

    assert '`.gitlab/build_agent.yaml` still points to `main`' in result.output
    assert 'Dispatched `update-build-agent-yaml.yml`' in result.output
    assert 'Tagging will continue.' in result.output
    dispatch_workflow.assert_called_once_with('update-build-agent-yaml.yml', 'master', {'branch': '7.56.x'})
    _assert_tag_pushed(stale_build_agent_yaml, result, '7.56.0-rc.1')


def test_build_agent_yaml_workflow_dispatch_waits_for_tag_confirmation(ddev, stale_build_agent_yaml, mocker):
    dispatch_workflow = mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow')

    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='n\n')

    assert result.exit_code == 1, result.output
    assert NO_CONFIRMATION_SO_ABORT in result.output
    dispatch_workflow.assert_not_called()
    stale_build_agent_yaml.push.assert_not_called()


def test_build_agent_yaml_workflow_dispatch_failure_warns_and_continues(ddev, stale_build_agent_yaml, mocker):
    mocker.patch(
        'ddev.utils.github.GitHubManager.dispatch_workflow',
        side_effect=_http_status_error(500, 'API error', method='POST'),
    )

    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    assert 'Warning: unable to trigger `update-build-agent-yaml.yml`: API error' in result.output
    assert 'gh workflow run update-build-agent-yaml.yml -f branch=7.56.x' in result.output
    assert 'Dispatched `update-build-agent-yaml.yml`' not in result.output
    _assert_tag_pushed(stale_build_agent_yaml, result, '7.56.0')


def test_build_agent_yaml_workflow_authentication_failure_uses_central_handler(ddev, stale_build_agent_yaml, mocker):
    mocker.patch(
        'ddev.utils.github.GitHubManager.dispatch_workflow',
        side_effect=GitHubAuthenticationError.from_http_status_error(
            _http_status_error(403, 'forbidden', method='POST')
        ),
    )

    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    assert result.exit_code == 1, result.output
    assert 'ddev config set github.token' in result.output
    assert 'gh workflow run update-build-agent-yaml.yml -f branch=7.56.x' in result.output
    stale_build_agent_yaml.tag.assert_called_once_with('7.56.0', message='7.56.0', ref=ORIGIN_REF)
    stale_build_agent_yaml.push.assert_called_once_with('7.56.0')


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

AGENT_BASE_COMMIT_SHA = 'a' * 40


def _mock_release_json(fake_async_github, release_json=AGENT_RELEASE_JSON):
    """Register the datadog-agent `release.json` the fake serves on `get_content`."""
    fake_async_github.mock_response(
        'get_content',
        FileContent(
            type='file',
            encoding='base64',
            size=len(release_json),
            name='release.json',
            path='release.json',
            content=base64.b64encode(release_json.encode()).decode(),
            sha='blobsha',
        ),
    )


def _committed_agent_pin(fake_async_github):
    """The `INTEGRATIONS_CORE_VERSION` value committed to the datadog-agent head branch."""
    committed = base64.b64decode(
        fake_async_github.last_call('create_or_update_file_contents').kwargs['content']
    ).decode()
    return json.loads(committed)['dependencies']['INTEGRATIONS_CORE_VERSION']


@pytest.fixture
def agent_pr(basic_git, mocker, github_credentials, fake_async_github):
    """The full pin-PR environment: the real `_open_datadog_agent_bump_pr`, valid GitHub
    credentials, and a datadog-agent `release.json` that still pins the branch name."""
    mocker.patch('ddev.cli.release.branch.tag._build_agent_yaml_points_to_main', return_value=False)
    mocker.patch('ddev.cli.release.branch.tag._open_datadog_agent_bump_pr', REAL_OPEN_DATADOG_AGENT_BUMP_PR)
    _mock_release_json(fake_async_github)
    basic_git.current_branch.return_value = '7.56.x'
    basic_git.tags.return_value = EXAMPLE_TAGS[:]
    return basic_git


def test_agent_pr_first_rc_of_milestone_targets_main(ddev, agent_pr, fake_async_github):
    """`X.Y.0-rc.1` is tagged before the Agent release branch is cut, so the pin goes to `main`."""
    agent_pr.tags.return_value = []

    result = _run_tag(ddev, '--skip-open-pr-check', input='\ny\n')

    _assert_tag_pushed(agent_pr, result, '7.56.0-rc.1')
    assert fake_async_github.last_call('get_ref').kwargs['ref'] == 'heads/main'
    # `release.json` is read at the commit SHA `get_ref` returned, not at the moving branch name.
    assert fake_async_github.last_call('get_content').kwargs['ref'] == AGENT_BASE_COMMIT_SHA
    assert fake_async_github.last_call('create_pull_request').kwargs['base'] == 'main'
    assert 'against `main`' in result.output


def test_agent_pr_later_rc_targets_release_branch(ddev, agent_pr, fake_async_github):
    result = _run_tag(ddev, '--skip-open-pr-check', input='\ny\n')

    _assert_tag_pushed(agent_pr, result, '7.56.0-rc.12')
    assert fake_async_github.last_call('get_content').kwargs['ref'] == AGENT_BASE_COMMIT_SHA
    assert fake_async_github.last_call('create_pull_request').kwargs['base'] == '7.56.x'


def test_agent_pr_patch_rc1_targets_release_branch(ddev, agent_pr, fake_async_github):
    """Only the first RC of a milestone targets `main`; a patch RC like `7.56.1-rc.1` does not."""
    agent_pr.tags.return_value = ['7.56.0']

    result = _run_tag(ddev, '--skip-open-pr-check', input='\ny\n')

    _assert_tag_pushed(agent_pr, result, '7.56.1-rc.1')
    assert fake_async_github.last_call('get_content').kwargs['ref'] == AGENT_BASE_COMMIT_SHA
    assert fake_async_github.last_call('create_pull_request').kwargs['base'] == '7.56.x'


def test_agent_pr_final_tag_targets_release_branch_and_bumps_pin(ddev, agent_pr, fake_async_github):
    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    _assert_tag_pushed(agent_pr, result, '7.56.0')
    assert fake_async_github.last_call('create_pull_request').kwargs['base'] == '7.56.x'
    # The committed release.json pins the integrations-core commit SHA the tag was placed on,
    # not the tag name.
    assert _committed_agent_pin(fake_async_github) == RESOLVED_COMMIT_SHA
    assert 'Datadog-agent bump PR: ' in result.output


def test_agent_pr_pins_the_ref_commit_not_the_branch_tip(ddev, agent_pr, fake_async_github):
    """`--ref` tags a non-tip commit; the pin must follow that commit, not the branch tip."""
    ref_commit_sha = 'cafef00d' * 5

    def dispatch(*args):
        # Give the `--ref` commit a distinct SHA from the branch tip so the test can tell the pin
        # followed the right one.
        if args[:2] == ('rev-parse', '--verify') and 'cafef00d' in args[2]:
            return f'{ref_commit_sha}\n'
        return _capture_dispatch(*args)

    agent_pr.capture.side_effect = dispatch

    result = _run_tag(ddev, '--final', '--ref', 'cafef00d', '--skip-open-pr-check', input='y\n')

    assert result.exit_code == 0, result.output
    assert f'at {ref_commit_sha}?' in result.output
    assert agent_pr.method_calls.count(c.tag('7.56.0', message='7.56.0', ref=ref_commit_sha)) == 1
    assert agent_pr.method_calls.count(c.push('7.56.0')) == 1
    assert _committed_agent_pin(fake_async_github) == ref_commit_sha


@pytest.mark.parametrize('indent', [4, 2], ids=['same-format', 'different-format'])
def test_agent_pr_skipped_when_pin_already_matches(ddev, agent_pr, fake_async_github, indent):
    """The skip is keyed on the pinned value, not on the file's exact serialization."""
    pinned = json.loads(AGENT_RELEASE_JSON)
    pinned['dependencies']['INTEGRATIONS_CORE_VERSION'] = RESOLVED_COMMIT_SHA
    _mock_release_json(fake_async_github, release_json=json.dumps(pinned, indent=indent) + '\n')

    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    assert result.exit_code == 0, result.output
    # Already pinned: no branch is cut, no commit is made, no PR is opened.
    fake_async_github.assert_not_called('create_or_update_file_contents')
    fake_async_github.assert_not_called('create_pull_request')
    assert f'already pins `{RESOLVED_COMMIT_SHA}`' in result.output


def test_agent_pr_creation_failure_prints_gh_command(ddev, agent_pr, fake_async_github):
    """A PR-creation failure happens after the head branch and pin commit exist, so only the PR
    is missing: the warning must carry the `gh` command that opens it."""
    fake_async_github.mock_response('create_pull_request', _http_status_error(500, method='POST'))

    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    _assert_tag_pushed(agent_pr, result, '7.56.0')
    assert 'could not be created' in result.output
    assert (
        'gh pr create --repo DataDog/datadog-agent --base 7.56.x --head integrations-core/bump-7.56.0 '
        "--title 'Bump integrations-core to 7.56.0'" in result.output
    )


def test_agent_pr_creation_uses_http_retries(ddev, agent_pr, fake_async_github):
    """PR creation passes a retry policy that retries server errors and pre-send transport errors,
    not 4xx responses."""
    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    _assert_tag_pushed(agent_pr, result, '7.56.0')
    retry = fake_async_github.last_call('create_pull_request').kwargs['retry']
    assert retry is not None
    assert retry.should_retry(_http_status_error(503, method='POST'))
    assert not retry.should_retry(_http_status_error(404, method='POST'))
    assert retry.attempts >= 2


def test_agent_pr_reports_when_release_branch_missing_on_agent(ddev, agent_pr, fake_async_github):
    """A 404 resolving the base branch means the Agent release branch isn't cut yet, or the
    token cannot see the repo, not a bug."""
    fake_async_github.mock_response('get_ref', _http_status_error(404, 'Not Found'))

    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    _assert_tag_pushed(agent_pr, result, '7.56.0')
    assert 'the `7.56.x` branch could not be found on datadog-agent' in result.output
    assert 'token has no access to DataDog/datadog-agent' in result.output


@pytest.mark.parametrize(
    'release_json',
    [
        pytest.param('This is not JSON', id='malformed'),
        pytest.param('{"current_milestone": "7.85.0"}', id='missing-dependencies'),
    ],
)
def test_agent_pr_malformed_release_json_degrades_gracefully(ddev, agent_pr, fake_async_github, release_json):
    """`release.json` comes from an external repo; bad JSON must degrade like any other failure.

    The tag was already pushed, so a crash here strands the user with no recovery hint."""
    _mock_release_json(fake_async_github, release_json=release_json)

    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    _assert_tag_pushed(agent_pr, result, '7.56.0')
    assert 'not the expected JSON shape' in result.output
    assert f'pinning `INTEGRATIONS_CORE_VERSION` to `{RESOLVED_COMMIT_SHA}`' in result.output
    fake_async_github.assert_not_called('create_or_update_file_contents')


def test_agent_pr_pin_commit_failure_reports_head_branch_state(ddev, agent_pr, fake_async_github):
    """The head branch already exists when the pin commit is attempted, so its failure message
    must report that branch rather than a generic hint that ignores it."""
    fake_async_github.mock_response('create_or_update_file_contents', _http_status_error(500, method='PUT'))

    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    _assert_tag_pushed(agent_pr, result, '7.56.0')
    assert 'integrations-core/bump-7.56.0` was created on datadog-agent' in result.output
    assert 'may not have been made' in result.output
    assert 'commit the pin to `integrations-core/bump-7.56.0` first' in result.output
    assert 'gh pr create --repo DataDog/datadog-agent' in result.output


def test_agent_pr_duplicate_creation_reports_existing_pr(ddev, agent_pr, fake_async_github):
    """A retried PR creation whose first attempt went through gets GitHub's 422
    "A pull request already exists"; the PR is there, so its URL must be reported."""
    existing_url = 'https://github.com/DataDog/datadog-agent/pull/123'
    fake_async_github.mock_response('create_pull_request', _http_status_error(422, method='POST'))
    fake_async_github.mock_response(
        'list_pull_requests', [PullRequest(number=123, html_url=existing_url, changed_files=1)]
    )

    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    _assert_tag_pushed(agent_pr, result, '7.56.0')
    assert f'Datadog-agent bump PR: {existing_url}' in result.output
    assert 'could not be created' not in result.output


def test_agent_pr_rejected_creation_with_no_existing_pr_prints_gh_command(ddev, agent_pr, fake_async_github):
    """A 422 that is not a duplicate (e.g. no commits between base and head) must not be
    swallowed: with no PR found, the recovery is the `gh` command, not silence."""
    fake_async_github.mock_response('create_pull_request', _http_status_error(422, method='POST'))

    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    _assert_tag_pushed(agent_pr, result, '7.56.0')
    assert 'could not be created' in result.output
    assert 'gh pr create --repo DataDog/datadog-agent' in result.output


def test_agent_pr_without_token_warns_and_pushes_tag(ddev, agent_pr, fake_async_github, config_file):
    config_file.model.github = {'user': 'test-user', 'token': ''}
    config_file.save()

    result = _run_tag(ddev, '--final', '--skip-open-pr-check', input='y\n')

    _assert_tag_pushed(agent_pr, result, '7.56.0')
    assert 'a GitHub token is required' in result.output
    assert (
        f'open one manually against `7.56.x` pinning `INTEGRATIONS_CORE_VERSION` to `{RESOLVED_COMMIT_SHA}`'
        in result.output
    )
    fake_async_github.assert_not_called('get_ref')


def test_bump_integrations_core_version_preserves_other_keys():
    result = _bump_integrations_core_version(AGENT_RELEASE_JSON, RESOLVED_COMMIT_SHA)

    data = json.loads(result)
    assert data['dependencies']['INTEGRATIONS_CORE_VERSION'] == RESOLVED_COMMIT_SHA
    assert data['dependencies']['JMXFETCH_VERSION'] == '0.49.5'
    assert data['current_milestone'] == '7.56.0'
    assert result.endswith('\n')
