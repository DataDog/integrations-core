# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from unittest import mock

import pytest
import tomli
import tomli_w


def test_pin(ddev, fake_repo):
    create_integration(fake_repo, 'foo', ['dep-a==1.0.0', 'dep-b==3.1.4'])
    create_integration(fake_repo, 'bar', ['dep-a==1.0.0'])

    result = ddev('dep', 'pin', 'dep-a==1.2.3')

    assert result.exit_code == 0
    assert result.output == 'Files updated: 2\n'

    assert_dependencies(fake_repo, 'foo', ['dep-a==1.2.3', 'dep-b==3.1.4'])
    assert_dependencies(fake_repo, 'bar', ['dep-a==1.2.3'])


def test_pin_non_canonical_name(ddev, fake_repo):
    create_integration(fake_repo, 'foo', ['non-canonical-dep==1.0.0'])

    # We use a non-canonical name, to assert that it gets recognized as the same as the
    # existing, canonical name
    result = ddev('dep', 'pin', 'non.Canonical_dep==1.2.3')

    assert result.exit_code == 0
    assert result.output == 'Files updated: 1\n'

    assert_dependencies(fake_repo, 'foo', ['non.Canonical_dep==1.2.3'])


def test_freeze(ddev, fake_repo):
    create_integration(fake_repo, 'foo', ['dep-a==1.0.0', 'dep-b==3.1.4'])
    create_integration(fake_repo, 'bar', ['dep-a==1.0.0', 'dep-c==5.1.0'])
    # datadog_checks_dev deps are not shipped with the agent
    create_integration(fake_repo, 'datadog_checks_dev', ['dep-d==4.4.4'])

    result = ddev('dep', 'freeze')

    agent_requirements_path = fake_repo / 'agent_requirements.in'

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
    create_integration(fake_repo, 'foo', ['dep-a==1.0.0', 'dep-b==3.1.4'])
    create_integration(fake_repo, 'bar', ['dep-a==1.0.0'])
    create_integration(fake_repo, 'datadog_checks_base', ['dep-a==1.0.0'])
    create_integration(fake_repo, 'datadog_checks_downloader', ['dep-a==1.0.0'])

    requirements = """
dep-a==1.1.1
dep-b==3.1.4
"""
    (fake_repo / 'agent_requirements.in').write_text(requirements.strip('\n'))

    result = ddev('dep', 'sync')

    assert result.exit_code == 0
    assert result.output == 'Files updated: 4\n'

    assert_dependencies(fake_repo, 'foo', ['dep-a==1.1.1', 'dep-b==3.1.4'])
    assert_dependencies(fake_repo, 'bar', ['dep-a==1.1.1'])
    assert_dependencies(fake_repo, 'datadog_checks_base', ['dep-a==1.1.1'])
    assert_dependencies(fake_repo, 'datadog_checks_base', ['dep-a==1.1.1'])


class TestUpdates:
    @pytest.fixture(autouse=True)
    def _setup(self, fake_repo, mock_async_http_get_json):
        self.repo = fake_repo
        self.dependencies = set()
        self.mock_response = mock_async_http_get_json

    def add_integration(self, name, deps):
        create_integration(self.repo, name, deps)
        self.dependencies.update(deps)

    def add_pypi_entry(self, name, releases):
        self.mock_response(
            f'https://pypi.org/pypi/{name}/json',
            {
                "info": {"name": name},
                "releases": releases,
            },
        )

    def write_requirements(self):
        self.requirements_path.write_text('\n'.join(sorted(self.dependencies)))

    @property
    def requirements_path(self):
        return self.repo / 'agent_requirements.in'

    def test_show_updates(self, ddev):
        self.add_integration('foo', ['dep-a==1.0.0', 'dep-b==3.1.4'])
        self.add_integration('bar', ['dep-a==1.0.0'])
        self.write_requirements()

        self.add_pypi_entry(
            'dep-a',
            {version: [{"python_version": "py2.py3", "requires_python": ">=2.7"}] for version in ["1.0.0", "1.2.3"]},
        )
        self.add_pypi_entry(
            'dep-b',
            {version: [{"python_version": "py2.py3", "requires_python": ">=2.7"}] for version in ["3.1.0", "3.1.4"]},
        )

        result = ddev('dep', 'updates')

        assert (
            result.output
            == '''1 dependencies are out of sync:
dep-a can be updated to version 1.2.3 on py2 and py3
'''
        )
        assert result.exit_code != 0

    def test_sync(self, ddev):
        self.add_integration('foo', ['dep-a==1.0.0', 'dep-b==3.1.4'])
        self.add_integration('bar', ['dep-a==1.0.0'])
        self.add_integration('datadog_checks_base', ['dep-a==1.0.0', 'dep-b==3.1.4'])
        self.add_integration('datadog_checks_downloader', ['dep-a==1.0.0', 'dep-b==3.1.4'])
        self.write_requirements()

        self.add_pypi_entry(
            'dep-a',
            {version: [{"python_version": "py2.py3", "requires_python": ">=2.7"}] for version in ["1.0.0", "1.2.3"]},
        )
        self.add_pypi_entry(
            'dep-b',
            {version: [{"python_version": "py2.py3", "requires_python": ">=2.7"}] for version in ["3.1.0", "3.1.4"]},
        )

        result = ddev('dep', 'updates', '--sync')

        assert result.exit_code == 0
        assert (
            result.output
            == '''Files updated: 4
Updated 1 dependencies
'''
        )

        assert_dependencies(self.repo, 'foo', ['dep-a==1.2.3', 'dep-b==3.1.4'])
        assert_dependencies(self.repo, 'bar', ['dep-a==1.2.3'])
        assert_dependencies(self.repo, 'datadog_checks_base', ['dep-a==1.2.3', 'dep-b==3.1.4'])
        assert_dependencies(self.repo, 'datadog_checks_downloader', ['dep-a==1.2.3', 'dep-b==3.1.4'])

        requirements = self.requirements_path.read_text()
        expected = """
dep-a==1.2.3
dep-b==3.1.4
"""
        assert requirements.strip('\n') == expected.strip('\n')

    def test_only_py3(self, ddev):
        self.add_integration('foo', ["dep-a==1.0.0; python_version > '3.0'"])
        self.write_requirements()

        self.add_pypi_entry(
            'dep-a',
            {version: [{"python_version": "py3", "requires_python": ">=3.6"}] for version in ["1.0.0", "1.2.3"]},
        )

        result = ddev('dep', 'updates')

        assert (
            result.output
            == '''1 dependencies are out of sync:
dep-a can be updated to version 1.2.3 on py3
'''
        )
        assert result.exit_code != 0

    def test_sync_only_py3(self, ddev):
        self.add_integration('foo', ["dep-a==1.0.0; python_version > '3.0'"])
        self.write_requirements()

        self.add_pypi_entry(
            'dep-a',
            {version: [{"python_version": "py3", "requires_python": ">=3.6"}] for version in ["1.0.0", "1.2.3"]},
        )

        result = ddev('dep', 'updates', '--sync')
        assert result.exit_code == 0
        assert (
            result.output
            == '''Files updated: 1
Updated 1 dependencies
'''
        )
        assert_dependencies(self.repo, 'foo', ["dep-a==1.2.3; python_version > '3.0'"])

        requirements = self.requirements_path.read_text()
        expected = """
dep-a==1.2.3; python_version > '3.0'
"""
        assert requirements.strip('\n') == expected.strip('\n')

    def test_ignored_deps(self, ddev, config_file):
        path = config_file.path.parent / '.ddev'
        path.mkdir(parents=True, exist_ok=True)
        (path / 'config.toml').write_text(
            """[overrides.dep.updates]
exclude = [
    'ddtrace',
]"""
        )

        self.add_integration('foo', ["ddtrace==1.0.0"])
        self.write_requirements()

        self.add_pypi_entry(
            'ddtrace',
            {version: [{"python_version": "py3", "requires_python": ">=3.6"}] for version in ["1.0.0", "1.2.3"]},
        )

        result = ddev('dep', 'updates')

        assert result.output == 'All dependencies are up to date\n'
        assert result.exit_code == 0

    def test_batch_size(self, ddev):
        deps = [f'dep-{suffix}' for suffix in ('a', 'b', 'c', 'd', 'e', 'f')]
        self.add_integration('foo', [f'{dep}==1.0.0' for dep in deps])
        self.write_requirements()

        for dep in deps:
            self.add_pypi_entry(
                dep,
                {version: [{"python_version": "py2.3", "requires_python": ">=2.7"}] for version in ["1.0.0", "1.2.3"]},
            )

        result = ddev('dep', 'updates', '--batch-size', '5')

        assert result.output.startswith('5 dependencies are out of sync:')
        assert result.exit_code != 0


@pytest.fixture
def mock_async_http_get_json():
    """Mock `get` responses assuming a JSON value is returned in the body.

    The mock will raise an exception if an unmatched URL is requested.

    It is somewhat coupled to the implementation as it makes many
    assumptions about how things are called and used.
    """

    url_responses = {}

    async def response_function(url, *args, **kwargs):
        if url in url_responses:
            response = mock.MagicMock()
            response.text = json.dumps(url_responses[url])
            return response

        response = mock.Mock()
        try:
            response.text = json.dumps(url_responses[url])
        except KeyError:
            # Avoid footguns and accidental requests
            raise RuntimeError(f"{url} didn't match any registered url's")

        return response

    fake_get = mock.AsyncMock(side_effect=response_function)

    def add_mock(url, response_value):
        url_responses[url] = response_value

    with mock.patch('httpx.AsyncClient.get', fake_get):
        yield add_mock


@pytest.fixture
def fake_repo(tmp_path, config_file):
    data_folder = tmp_path / 'datadog_checks_base' / 'datadog_checks' / 'base' / 'data'
    data_folder.mkdir(parents=True)

    # Set this as core repo in the config
    config_file.model.repos['core'] = str(tmp_path)
    config_file.save()

    yield tmp_path


def assert_dependencies(root, name, dependencies):
    with open(root / name / 'pyproject.toml', 'rb') as f:
        assert tomli.load(f)['project']['optional-dependencies']['deps'] == dependencies


def create_integration(root, name, dependencies):
    integration_dir = root / name
    integration_dir.mkdir(exist_ok=True)
    with open(integration_dir / 'pyproject.toml', 'wb') as f:
        tomli_w.dump({'project': {'optional-dependencies': {'deps': dependencies}}}, f)

    # Fill stuff needed for it to be recognized as an agent check
    (integration_dir / 'datadog_checks' / name).mkdir(parents=True)
    (integration_dir / 'datadog_checks' / name / '__about__.py').touch()
    (integration_dir / 'datadog_checks' / name / '__init__.py').write_text(
        """
import a
import b
"""
    )
