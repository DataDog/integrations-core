# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.cli.release.branch.create import ensure_build_agent_yaml_updated
from ddev.utils.fs import Path


@pytest.mark.parametrize(
    'name',
    [
        pytest.param("7.5.2", id='does not end with ".x"'),
        pytest.param("7.5.6.x", id='too many parts'),
        pytest.param("7.x", id='not enough parts'),
    ],
)
def test_create_invalid_branch_name(ddev, name):
    result = ddev('release', 'branch', 'create', name)
    assert result.exit_code == 1, result.output
    assert f'Invalid branch name: {name}. Branch name must match the pattern ^\\d+\\.\\d+\\.x$\n' in result.output


@pytest.mark.parametrize(
    'yaml_updated,expected_git_call_count',
    [
        pytest.param(True, 6, id='agent_branch_exists'),
        pytest.param(False, 4, id='agent_branch_not_exists'),
    ],
)
def test_create_branch(ddev, mocker, yaml_updated, expected_git_call_count):
    """Test branch creation with and without agent branch existing."""
    run_mock = mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.github.GitHubManager.create_label')
    mocker.patch('ddev.cli.release.branch.create.ensure_build_agent_yaml_updated', return_value=yaml_updated)

    result = ddev('release', 'branch', 'create', '5.5.x')

    assert result.exit_code == 0, result.output
    assert len(run_mock.call_args_list) == expected_git_call_count


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
