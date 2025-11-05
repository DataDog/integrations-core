# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.cli.release.branch.create import update_build_agent_yaml
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


def test_create_branch(ddev, mocker):
    run_mock = mocker.patch('ddev.utils.git.GitRepository.run')
    create_label_mock = mocker.patch('ddev.utils.github.GitHubManager.create_label')

    result = ddev('release', 'branch', 'create', '5.5.x')

    assert result.exit_code == 0, result.output

    assert run_mock.call_args_list == [
        mocker.call('checkout', 'master'),
        mocker.call('pull', 'origin', 'master'),
        mocker.call('checkout', '-B', '5.5.x'),
        mocker.call('add', '.gitlab/build_agent.yaml'),
        mocker.call('commit', '-m', 'Update build_agent.yaml to use agent branch: 5.5.x'),
        mocker.call('push', 'origin', '5.5.x'),
    ]

    assert create_label_mock.call_args_list == [
        mocker.call('backport/5.5.x', '5319e7'),
    ]


def test_update_build_agent_yaml_success(mocker, tmp_path):
    """Test successful update of build_agent.yaml"""

    # Create a temporary build_agent.yaml file
    build_agent_path = Path(tmp_path / '.gitlab' / 'build_agent.yaml')
    build_agent_path.parent.ensure_dir_exists()

    original_content = """---
.build-agent-tpl:
  variables:
    RELEASE_VERSION_6: "nightly"
    RELEASE_VERSION_7: "nightly-a7"
  trigger:
    project: DataDog/datadog-agent
    branch: main
    strategy: depend

build-agent-auto:
  extends: .build-agent-tpl
  rules:
    - if: $CI_COMMIT_BRANCH =~ /^7\\.\\d+\\.x$/
      when: never
"""

    build_agent_path.write_text(original_content)

    app_mock = mocker.MagicMock()

    with Path(tmp_path).as_cwd():
        update_build_agent_yaml(app_mock, '7.99.x')

    updated_content = build_agent_path.read_text()

    assert 'branch: 7.99.x' in updated_content
    assert 'branch: main' not in updated_content
