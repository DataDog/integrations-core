# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import tomli
import tomli_w
from datadog_checks.dev.tooling.utils import get_root, set_root


def test_pin(ddev, fake_repo):
    create_integration(fake_repo, 'foo', ['dep-a==1.0.0', 'dep-b==3.1.4'])
    create_integration(fake_repo, 'bar', ['dep-a==1.0.0'])

    result = ddev('dep', 'pin', 'dep-a==1.2.3')

    assert result.exit_code == 0
    assert result.output == 'Files updated: 2\n'

    assert_dependencies(fake_repo, 'foo', ['dep-a==1.2.3', 'dep-b==3.1.4'])
    assert_dependencies(fake_repo, 'bar', ['dep-a==1.2.3'])


def test_freeze(ddev, fake_repo):
    create_integration(fake_repo, 'foo1', ['dep-a==1.0.0', 'dep-b==3.1.4'])
    create_integration(fake_repo, 'bar1', ['dep-a==1.0.0', 'dep-c==5.1.0'])
    # datadog_checks_dev deps are not shipped with the agent
    create_integration(fake_repo, 'datadog_checks_dev', ['dep-d==4.4.4'])

    result = ddev('dep', 'freeze')

    agent_requirements_path = (
        fake_repo / 'datadog_checks_base' / 'datadog_checks' / 'base' / 'data' / 'agent_requirements.in'
    )

    assert result.exit_code == 0
    assert result.output == f'Static file: {agent_requirements_path}\n'

    requirements = agent_requirements_path.read_text()

    expected = """
dep-a==1.0.0
dep-b==3.1.4
dep-c==5.1.0
"""
    assert requirements.strip('\n') == expected.strip('\n')


def test_sync(ddev, fake_repo):
    create_integration(fake_repo, 'foo2', ['dep-a==1.0.0', 'dep-b==3.1.4'])
    create_integration(fake_repo, 'bar2', ['dep-a==1.0.0'])

    requirements = """
dep-a==1.1.1
dep-b==3.1.4
"""
    (fake_repo / 'datadog_checks_base' / 'datadog_checks' / 'base' / 'data' / 'agent_requirements.in').write_text(
        requirements.strip('\n')
    )

    result = ddev('dep', 'sync')

    assert result.exit_code == 0
    assert result.output == 'Files updated: 2\n'

    assert_dependencies(fake_repo, 'foo2', ['dep-a==1.1.1', 'dep-b==3.1.4'])
    assert_dependencies(fake_repo, 'bar2', ['dep-a==1.1.1'])


@pytest.fixture
def fake_repo(tmp_path, config_file):
    data_folder = tmp_path / 'datadog_checks_base' / 'datadog_checks' / 'base' / 'data'
    data_folder.mkdir(parents=True)

    # Set this as core repo in the config
    config_file.model.repos['core'] = str(tmp_path)
    config_file.save()

    # XXX: Remove the root manipulation once the commands are ported over
    old_root = get_root()
    set_root(str(tmp_path))
    yield tmp_path
    set_root(old_root)


def assert_dependencies(root, name, dependencies):
    with open(root / name / 'pyproject.toml', 'rb') as f:
        assert tomli.load(f)['project']['optional-dependencies']['deps'] == dependencies


def create_integration(root, name, dependencies):
    integration_dir = root / name
    integration_dir.mkdir()
    with open(integration_dir / 'pyproject.toml', 'wb') as f:
        tomli_w.dump({'project': {'optional-dependencies': {'deps': dependencies}}}, f)

    # We need the version file for it to be recognized as an integration by the old code
    (integration_dir / 'datadog_checks' / name).mkdir(parents=True)
    (integration_dir / 'datadog_checks' / name / '__about__.py').touch()
