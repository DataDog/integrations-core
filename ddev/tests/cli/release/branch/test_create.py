# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from unittest.mock import call

import pytest

from ddev.cli.release.branch.create import compute_next_milestone, ensure_build_agent_yaml_updated, update_release_json
from ddev.utils.fs import Path


@pytest.mark.parametrize(
    'name',
    [
        pytest.param("7.5.2", id='does not end with ".x"'),
        pytest.param("7.5.6.x", id='too many parts'),
        pytest.param("7.x", id='not enough parts'),
    ],
)
def test_create_invalid_branch_name(ddev, name, mocker):
    # Mock the confirmation to bypass it (we're testing validation, not confirmation)
    mocker.patch('click.confirm', return_value=True)

    result = ddev('release', 'branch', 'create', name)
    assert result.exit_code == 1, result.output
    assert f'Invalid branch name: {name}. Branch name must match the pattern ^\\d+\\.\\d+\\.x$\n' in result.output


@pytest.mark.parametrize(
    'yaml_updated',
    [
        pytest.param(True, id='agent_branch_exists'),
        pytest.param(False, id='agent_branch_not_exists'),
    ],
)
def test_create_branch(ddev, mocker, yaml_updated):
    """Test that the full git workflow is executed correctly."""
    run_mock = mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.github.GitHubManager.create_label')
    mocker.patch('ddev.utils.github.GitHubManager.create_milestone')
    mocker.patch('ddev.utils.github.GitHubManager.create_pull_request', return_value='https://github.com/test/pr/1')
    mocker.patch('ddev.cli.release.branch.create.ensure_build_agent_yaml_updated', return_value=yaml_updated)
    mocker.patch('ddev.cli.release.branch.create.update_release_json')
    mocker.patch('click.confirm', return_value=True)

    result = ddev('release', 'branch', 'create', '5.5.x')

    assert result.exit_code == 0, result.output

    # Release branch workflow
    run_mock.assert_any_call('checkout', 'master')
    run_mock.assert_any_call('pull', 'origin', 'master')
    run_mock.assert_any_call('checkout', '-B', '5.5.x')
    run_mock.assert_any_call('push', 'origin', '5.5.x')

    # yaml commit only happens when agent branch exists
    yaml_commit = call('add', '.gitlab/build_agent.yaml')
    assert (yaml_commit in run_mock.call_args_list) is yaml_updated

    # Milestone bump workflow
    run_mock.assert_any_call('fetch', 'origin', 'master')
    run_mock.assert_any_call('checkout', '-B', 'release/bump-milestone-5.6.0', 'origin/master')
    run_mock.assert_any_call('add', 'release.json')
    run_mock.assert_any_call('commit', '-m', 'Update current_milestone to 5.6.0')
    run_mock.assert_any_call('push', 'origin', 'release/bump-milestone-5.6.0')


@pytest.mark.parametrize(
    'ls_remote_output,expected_result,file_should_change',
    [
        pytest.param('abc123\trefs/heads/7.99.x\n', True, True, id='branch_exists'),
        pytest.param('', False, False, id='branch_not_exists'),
    ],
)
def test_ensure_build_agent_yaml_updated(mocker, tmp_path, ls_remote_output, expected_result, file_should_change):
    """Test ensure_build_agent_yaml_updated with different branch existence scenarios."""
    build_agent_path = Path(tmp_path / '.gitlab' / 'build_agent.yaml')
    build_agent_path.parent.ensure_dir_exists()
    build_agent_path.write_text('.build-agent-tpl:\n  trigger:\n    branch: main\n')

    app_mock = mocker.MagicMock()
    app_mock.repo.git.capture.return_value = ls_remote_output

    with Path(tmp_path).as_cwd():
        result = ensure_build_agent_yaml_updated(app_mock, '7.99.x')

    assert result is expected_result
    content = build_agent_path.read_text()
    if file_should_change:
        assert 'branch: 7.99.x' in content
    else:
        assert 'branch: main' in content


def test_ensure_build_agent_yaml_updated_already_on_release_branch(mocker, tmp_path):
    """Test early return when file already points to a release branch."""
    build_agent_path = Path(tmp_path / '.gitlab' / 'build_agent.yaml')
    build_agent_path.parent.ensure_dir_exists()
    build_agent_path.write_text('.build-agent-tpl:\n  trigger:\n    branch: 7.98.x\n')

    app_mock = mocker.MagicMock()

    with Path(tmp_path).as_cwd():
        result = ensure_build_agent_yaml_updated(app_mock, '7.99.x')

    assert result is False
    app_mock.repo.git.capture.assert_not_called()


def test_ensure_build_agent_yaml_updated_file_not_found(mocker, tmp_path):
    """Test graceful handling when build_agent.yaml does not exist."""
    app_mock = mocker.MagicMock()

    with Path(tmp_path).as_cwd():
        result = ensure_build_agent_yaml_updated(app_mock, '7.99.x')

    assert result is False
    app_mock.display_warning.assert_called_once()


def test_create_branch_confirmation_required(ddev, mocker):
    mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.github.GitHubManager.create_label')
    mocker.patch('ddev.utils.github.GitHubManager.create_milestone')
    mocker.patch('ddev.utils.github.GitHubManager.create_pull_request', return_value='https://github.com/test/pr/1')
    mocker.patch('ddev.cli.release.branch.create.ensure_build_agent_yaml_updated', return_value=False)
    mocker.patch('ddev.cli.release.branch.create.update_release_json')
    mocker.patch('click.confirm', return_value=False)

    result = ddev('release', 'branch', 'create', '5.5.x')

    assert result.exit_code == 1, result.output
    assert 'Did not get confirmation' in result.output


def test_create_branch_with_suggestion(ddev, mocker):
    mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.git.GitRepository.capture', return_value='  origin/7.77.x\n  origin/7.76.x\n')
    mocker.patch('ddev.utils.github.GitHubManager.create_label')
    mocker.patch('ddev.utils.github.GitHubManager.create_milestone')
    mocker.patch('ddev.utils.github.GitHubManager.create_pull_request', return_value='https://github.com/test/pr/1')
    mocker.patch('ddev.cli.release.branch.create.ensure_build_agent_yaml_updated', return_value=False)
    mocker.patch('ddev.cli.release.branch.create.update_release_json')
    mocker.patch('click.prompt', return_value='7.78.x')
    mocker.patch('click.confirm', return_value=True)

    result = ddev('release', 'branch', 'create')

    assert result.exit_code == 0, result.output
    assert 'Creating the release branch `7.78.x`' in result.output


def test_create_branch_with_gap_suggests_missing_branch(ddev, mocker):
    mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.git.GitRepository.capture', return_value='  origin/7.62.x\n  origin/7.60.x\n')
    mocker.patch('ddev.utils.github.GitHubManager.create_label')
    mocker.patch('ddev.utils.github.GitHubManager.create_milestone')
    mocker.patch('ddev.utils.github.GitHubManager.create_pull_request', return_value='https://github.com/test/pr/1')
    mocker.patch('ddev.cli.release.branch.create.ensure_build_agent_yaml_updated', return_value=False)
    mocker.patch('ddev.cli.release.branch.create.update_release_json')
    mocker.patch('click.prompt', return_value='7.61.x')
    mocker.patch('click.confirm', return_value=True)

    result = ddev('release', 'branch', 'create')

    assert result.exit_code == 0, result.output
    assert 'Gap detected' in result.output
    assert 'Creating the release branch `7.61.x`' in result.output


@pytest.mark.parametrize(
    'branch_name,expected_milestone',
    [
        pytest.param('7.79.x', '7.80.0', id='standard_minor_bump'),
        pytest.param('7.0.x', '7.1.0', id='zero_minor'),
        pytest.param('8.5.x', '8.6.0', id='different_major'),
    ],
)
def test_compute_next_milestone(branch_name, expected_milestone):
    assert compute_next_milestone(branch_name) == expected_milestone


def test_update_release_json(tmp_path):
    release_json = Path(tmp_path / 'release.json')
    release_json.write_text('{\n\t"current_milestone": "7.79.0"\n}\n')

    update_release_json(release_json, '7.80.0')

    data = json.loads(release_json.read_text())
    assert data['current_milestone'] == '7.80.0'


def test_update_release_json_file_not_found(tmp_path):
    release_json = Path(tmp_path / 'release.json')
    assert not release_json.exists()

    update_release_json(release_json, '7.80.0')

    assert release_json.exists()
    data = json.loads(release_json.read_text())
    assert data == {'current_milestone': '7.80.0'}


def test_create_branch_creates_milestone_and_pr(ddev, mocker):
    mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.github.GitHubManager.create_label')
    mocker.patch('ddev.utils.github.GitHubManager.create_milestone')
    mocker.patch('ddev.utils.github.GitHubManager.create_pull_request', return_value='https://github.com/test/pr/1')
    mocker.patch('ddev.cli.release.branch.create.ensure_build_agent_yaml_updated', return_value=False)
    mocker.patch('ddev.cli.release.branch.create.update_release_json')
    mocker.patch('click.confirm', return_value=True)

    result = ddev('release', 'branch', 'create', '7.79.x')

    assert result.exit_code == 0, result.output
    assert 'Creating the `7.80.0` milestone' in result.output
    assert 'Updating release.json with new milestone `7.80.0`' in result.output
    assert 'Pull request created' in result.output
    assert 'All done' in result.output


def test_create_branch_milestone_already_exists(ddev, mocker):
    from httpx import HTTPStatusError, Request, Response

    mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.github.GitHubManager.create_label')
    mocker.patch('ddev.utils.github.GitHubManager.create_milestone').side_effect = HTTPStatusError(
        'Validation Failed',
        request=Request('POST', 'https://api.github.com/repos/test/milestones'),
        response=Response(422),
    )
    mocker.patch('ddev.utils.github.GitHubManager.create_pull_request', return_value='https://github.com/test/pr/1')
    mocker.patch('ddev.cli.release.branch.create.ensure_build_agent_yaml_updated', return_value=False)
    mocker.patch('ddev.cli.release.branch.create.update_release_json')
    mocker.patch('click.confirm', return_value=True)

    result = ddev('release', 'branch', 'create', '7.79.x')

    assert result.exit_code == 0, result.output
    assert 'already exists' in result.output
    assert 'Pull request created' in result.output
    assert 'All done' in result.output


def test_create_branch_push_failure(ddev, mocker):
    def push_fails(*args):
        if args == ('push', 'origin', 'release/bump-milestone-7.80.0'):
            raise OSError('push failed')

    mocker.patch('ddev.utils.git.GitRepository.run', side_effect=push_fails)
    mocker.patch('ddev.utils.github.GitHubManager.create_label')
    mocker.patch('ddev.utils.github.GitHubManager.create_milestone')
    create_pr_mock = mocker.patch(
        'ddev.utils.github.GitHubManager.create_pull_request', return_value='https://github.com/test/pr/1'
    )
    mocker.patch('ddev.cli.release.branch.create.ensure_build_agent_yaml_updated', return_value=False)
    mocker.patch('ddev.cli.release.branch.create.update_release_json')
    mocker.patch('click.confirm', return_value=True)

    result = ddev('release', 'branch', 'create', '7.79.x')

    assert result.exit_code == 0, result.output
    assert 'Failed to push the branch' in result.output
    assert 'git push origin release/bump-milestone-7.80.0' in result.output
    create_pr_mock.assert_not_called()


def test_create_branch_pr_creation_failure(ddev, mocker):
    mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.github.GitHubManager.create_label')
    mocker.patch('ddev.utils.github.GitHubManager.create_milestone')
    mocker.patch('ddev.utils.github.GitHubManager.create_pull_request', side_effect=Exception('API error'))
    mocker.patch('ddev.cli.release.branch.create.ensure_build_agent_yaml_updated', return_value=False)
    mocker.patch('ddev.cli.release.branch.create.update_release_json')
    mocker.patch('click.confirm', return_value=True)

    result = ddev('release', 'branch', 'create', '7.79.x')

    assert result.exit_code == 0, result.output
    assert 'Failed to create the pull request' in result.output
    assert 'All done' in result.output
