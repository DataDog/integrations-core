import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

import dependency_wheel_promotion_gate as gate


class FakeGitHub:
    def __init__(self, *, files=None, commits=None, commit_files=None, statuses=None, comments=None):
        self.files = files or []
        self.commits = commits or []
        self.commit_files_by_sha = commit_files or {}
        self.statuses = list(statuses or [])
        self.comments = list(comments or [])
        self.created_statuses = []
        self.created_comments = []
        self.updated_comments = []

    def pull_request_files(self, _pr_number):
        return self.files

    def pull_request_commits(self, _pr_number):
        return self.commits

    def commit_files(self, sha):
        return self.commit_files_by_sha[sha]

    def current_status(self, _sha):
        return self.statuses.pop(0) if self.statuses else None

    def create_status(self, sha, state, description, target_url=None):
        self.created_statuses.append((sha, state, description, target_url))

    def issue_comments(self, _pr_number):
        return self.comments

    def create_comment(self, pr_number, body):
        self.created_comments.append((pr_number, body))
        return 101

    def update_comment(self, comment_id, body):
        self.updated_comments.append((comment_id, body))
        return comment_id


def pr_file(filename, *, status='modified', previous_filename=None):
    result = {'filename': filename, 'status': status}
    if previous_filename:
        result['previous_filename'] = previous_filename
    return result


def pull_request_event(files, *, commits=0, fork=False):
    return {
        'repository': {'full_name': 'DataDog/integrations-core'},
        'pull_request': {
            'number': 123,
            'html_url': 'https://github.com/DataDog/integrations-core/pull/123',
            'changed_files': len(files),
            'commits': commits,
            'head': {
                'sha': 'head-sha',
                'ref': 'feature',
                'repo': {'full_name': 'someone/fork' if fork else 'DataDog/integrations-core'},
            },
        },
    }


def assess(files, *, commits=None, commit_files=None, event_changes=None, event_commits=None, fork=False):
    commits = commits or []
    event = pull_request_event(files, commits=len(commits), fork=fork)
    if event_changes is not None:
        event['pull_request']['changed_files'] = event_changes
    if event_commits is not None:
        event['pull_request']['commits'] = event_commits
    client = FakeGitHub(files=files, commits=commits, commit_files=commit_files)
    return gate.assess_pull_request(event, client, 'https://github.com/run')


def test_non_dependency_change_is_not_applicable():
    result = assess([pr_file('README.md')])
    assert result.state == gate.PromotionState.NOT_APPLICABLE
    assert not result.check_promotion


def test_dependency_change_on_a_fork_is_blocked_as_a_fork():
    result = assess([pr_file('agent_requirements.in')], fork=True)
    assert result.state == gate.PromotionState.FORK


def test_dependency_input_without_output_awaits_resolution():
    result = assess([pr_file('agent_requirements.in')])
    assert result.state == gate.PromotionState.AWAITING_RESOLUTION


def test_current_resolution_output_is_ready_for_promotion_check():
    files = [pr_file('agent_requirements.in'), pr_file('.deps/resolved/linux.txt')]
    commits = [{'sha': 'input'}, {'sha': 'output'}]
    result = assess(
        files,
        commits=commits,
        commit_files={
            'output': [pr_file('.deps/resolved/linux.txt')],
            'input': [pr_file('agent_requirements.in')],
        },
    )
    assert result.state == gate.PromotionState.AWAITING_PROMOTION
    assert result.check_promotion


def test_dependency_change_after_output_awaits_resolution_again():
    files = [pr_file('agent_requirements.in'), pr_file('.deps/resolved/linux.txt')]
    commits = [{'sha': 'output'}, {'sha': 'input'}]
    result = assess(
        files,
        commits=commits,
        commit_files={
            'input': [pr_file('agent_requirements.in')],
            'output': [pr_file('.deps/resolved/linux.txt')],
        },
    )
    assert result.state == gate.PromotionState.AWAITING_RESOLUTION


@pytest.mark.parametrize(
    'promoted,expected',
    [('false', gate.PromotionState.AWAITING_PROMOTION), ('true', gate.PromotionState.PROMOTED)],
)
def test_verification_finishes_the_state(promoted, expected):
    assessment = assess(
        [pr_file('.deps/resolved/linux.txt')],
        commits=[{'sha': 'output'}],
        commit_files={'output': [pr_file('.deps/resolved/linux.txt')]},
    )
    result = gate.finish_state(
        assessment,
        lockfiles_outcome='success',
        verify_outcome='success',
        promoted=promoted,
    )
    assert result.state == expected


@pytest.mark.parametrize(
    'lockfiles_outcome,verify_outcome,promoted,reason',
    [
        ('failure', 'skipped', '', 'lockfiles'),
        ('success', 'failure', '', 'Stable wheel storage'),
        ('success', 'success', '', 'Stable wheel storage'),
    ],
)
def test_failed_verification_is_indeterminate(lockfiles_outcome, verify_outcome, promoted, reason):
    assessment = replace(
        assess([pr_file('agent_requirements.in')]),
        state=gate.PromotionState.AWAITING_PROMOTION,
        check_promotion=True,
    )
    result = gate.finish_state(
        assessment,
        lockfiles_outcome=lockfiles_outcome,
        verify_outcome=verify_outcome,
        promoted=promoted,
    )
    assert result.state == gate.PromotionState.INDETERMINATE
    assert reason in result.reason


def test_incomplete_pull_request_file_list_fails_closed():
    result = assess([pr_file('README.md')], event_changes=3001)
    assert result.state == gate.PromotionState.INDETERMINATE
    assert '1 of 3001 changed files' in result.reason


def test_incomplete_pull_request_commit_list_fails_closed():
    files = [pr_file('.deps/resolved/linux.txt')]
    result = assess(files, commits=[{'sha': 'output'}], event_commits=251, commit_files={})
    assert result.state == gate.PromotionState.INDETERMINATE
    assert '1 of 251 pull request commits' in result.reason


def test_copying_an_input_to_an_ignored_path_does_not_change_resolution():
    copied = pr_file(
        '.builders/tests/copied_build.py',
        status='copied',
        previous_filename='.builders/build.py',
    )
    assert assess([copied]).state == gate.PromotionState.NOT_APPLICABLE


def test_renaming_an_input_to_an_ignored_path_changes_resolution():
    renamed = pr_file(
        '.builders/tests/moved_build.py',
        status='renamed',
        previous_filename='.builders/build.py',
    )
    assert assess([renamed]).state == gate.PromotionState.AWAITING_RESOLUTION


def test_large_commit_fails_closed():
    files = [pr_file('.deps/resolved/linux.txt')]
    commit_files = [pr_file(f'file-{index}') for index in range(gate.COMMIT_FILE_LIMIT)]
    result = assess(files, commits=[{'sha': 'large'}], commit_files={'large': commit_files})
    assert result.state == gate.PromotionState.INDETERMINATE
    assert 'cannot be inspected completely' in result.reason


def test_walk_is_bounded_to_the_latest_commits():
    commits = [{'sha': f'commit-{index}'} for index in range(gate.WALK_LIMIT + 1)]
    commit_files = {item['sha']: [pr_file('README.md')] for item in commits}
    commit_files['commit-0'] = [pr_file('.deps/resolved/linux.txt')]
    result = assess(
        [pr_file('.deps/resolved/linux.txt')],
        commits=commits,
        commit_files=commit_files,
    )
    assert result.state == gate.PromotionState.AWAITING_RESOLUTION


@pytest.mark.parametrize(
    'state,expected_text',
    [
        (gate.PromotionState.FORK, 'maintainer must reopen'),
        (gate.PromotionState.AWAITING_RESOLUTION, 'Do not promote early'),
        (gate.PromotionState.AWAITING_PROMOTION, 'ask an `agent-integrations` maintainer'),
        (gate.PromotionState.PROMOTED, 'every pinned wheel is in stable storage'),
        (gate.PromotionState.INDETERMINATE, 'could not be determined safely'),
    ],
)
def test_notice_explains_the_operational_state(state, expected_text):
    assessment = gate.Assessment(
        state=state,
        repository='DataDog/integrations-core',
        pr_number=123,
        pr_url='https://github.com/DataDog/integrations-core/pull/123',
        head_sha='deadbeef',
        head_ref='feature',
        run_url='https://github.com/run',
        reason='GitHub returned incomplete data.',
    )
    notice = gate.render_notice(assessment)
    assert expected_text in notice
    assert 'deadbeef' in notice
    assert gate.comment_marker(123) in notice


def test_publish_updates_the_marker_comment_and_status():
    assessment = gate.Assessment(
        state=gate.PromotionState.AWAITING_RESOLUTION,
        repository='DataDog/integrations-core',
        pr_number=123,
        pr_url='https://github.com/DataDog/integrations-core/pull/123',
        head_sha='deadbeef',
        head_ref='feature',
        run_url='https://github.com/run',
    )
    client = FakeGitHub(
        comments=[
            {
                'id': 77,
                'body': gate.comment_marker(123),
                'user': {'login': gate.COMMENT_AUTHOR},
            }
        ]
    )
    gate.publish(client, assessment)
    assert client.created_comments == []
    assert client.updated_comments[0][0] == 77
    assert client.created_statuses == [
        ('deadbeef', 'pending', 'Waiting for dependency resolution.', assessment.pr_url + '#issuecomment-77')
    ]


def test_publish_does_not_overwrite_a_newer_promotion_result():
    assessment = gate.Assessment(
        state=gate.PromotionState.AWAITING_PROMOTION,
        repository='DataDog/integrations-core',
        pr_number=123,
        pr_url='https://github.com/DataDog/integrations-core/pull/123',
        head_sha='deadbeef',
        head_ref='feature',
        run_url='https://github.com/run',
    )
    client = FakeGitHub(statuses=[None, {'state': 'success'}])
    gate.publish(client, assessment)
    assert client.created_comments == []
    assert client.created_statuses == []


def test_not_applicable_does_not_create_a_notice():
    assessment = gate.Assessment(
        state=gate.PromotionState.NOT_APPLICABLE,
        repository='DataDog/integrations-core',
        pr_number=123,
        pr_url='https://github.com/DataDog/integrations-core/pull/123',
        head_sha='deadbeef',
        head_ref='feature',
        run_url='https://github.com/run',
    )
    client = FakeGitHub()
    gate.publish(client, assessment)
    assert client.created_comments == []
    assert client.created_statuses[0][1] == 'success'


def test_pagination_follows_the_next_link_on_the_same_api_host():
    client = gate.GitHubClient('token', 'DataDog/integrations-core')
    client.request = Mock(
        side_effect=[
            ([{'id': 1}], {'link': '<https://api.github.com/resource?page=2>; rel="next"'}),
            ([{'id': 2}], {}),
        ]
    )
    assert client.paginate('/resource') == [{'id': 1}, {'id': 2}]
    assert client.request.call_args_list[1].args == ('GET', '/resource')
    assert client.request.call_args_list[1].kwargs['params'] == {'page': '2'}


def test_settled_status_stands_down_without_overwriting_it(monkeypatch, tmp_path):
    event = pull_request_event([pr_file('agent_requirements.in')])
    client = FakeGitHub(statuses=[{'state': 'success'}])
    state_path = tmp_path / 'state.json'
    monkeypatch.setattr(gate, '_environment', lambda: (event, client, 'https://github.com/run', state_path))
    gate.command_assess()
    assert not gate.Assessment.read(state_path).evaluate
    assert client.created_statuses == []


def test_unknown_persisted_state_is_rejected(tmp_path: Path):
    path = tmp_path / 'assessment.json'
    path.write_text(
        json.dumps(
            {
                'state': 'unknown',
                'repository': 'o/r',
                'pr_number': 1,
                'pr_url': 'u',
                'head_sha': 's',
                'head_ref': 'b',
                'run_url': 'r',
            }
        )
    )
    with pytest.raises(ValueError, match='unknown'):
        gate.Assessment.read(path)


def test_assess_command_blocks_before_a_later_api_failure(monkeypatch, tmp_path):
    event = pull_request_event([pr_file('agent_requirements.in')])
    client = FakeGitHub(files=[pr_file('agent_requirements.in')])

    def fail(_pr_number):
        raise RuntimeError('API unavailable')

    client.pull_request_files = fail
    state_path = tmp_path / 'state.json'
    monkeypatch.setattr(gate, '_environment', lambda: (event, client, 'https://github.com/run', state_path))
    with pytest.raises(RuntimeError, match='API unavailable'):
        gate.command_assess()
    assert client.created_statuses == [
        ('head-sha', 'pending', 'Checking wheel promotion.', 'https://github.com/run')
    ]


def test_merge_queue_publishes_success(monkeypatch, tmp_path):
    event = {
        'repository': {'full_name': 'DataDog/integrations-core'},
        'merge_group': {'head_sha': 'merge-sha'},
    }
    client = FakeGitHub()
    monkeypatch.setattr(gate, '_environment', lambda: (event, client, 'https://github.com/run', tmp_path / 'state'))
    gate.command_merge_queue()
    assert client.created_statuses == [
        ('merge-sha', 'success', 'Promotion requirement was validated on the PR head.', 'https://github.com/run')
    ]
