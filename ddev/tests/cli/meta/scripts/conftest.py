# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.repo.core import Repository


@pytest.fixture
def fake_repo(tmp_path_factory, config_file, ddev):
    repo_path = tmp_path_factory.mktemp('integrations-core')
    repo = Repository('integrations-core', str(repo_path))

    config_file.model.repos['core'] = str(repo.path)
    config_file.save()

    write_file(
        repo_path / 'ddev' / 'src' / 'ddev' / 'repo',
        'constants.py',
        """# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
CONFIG_DIRECTORY = '.ddev'
NOT_SHIPPABLE = frozenset(['datadog_checks_dev', 'datadog_checks_tests_helper', 'ddev'])
FULL_NAMES = {
    'core': 'integrations-core',
    'extras': 'integrations-extras',
    'marketplace': 'marketplace',
    'agent': 'datadog-agent',
}

# This is automatically maintained
PYTHON_VERSION = '3.9'
""",
    )

    write_file(
        repo_path / 'dummy',
        'hatch.toml',
        """[env.collectors.datadog-checks]

[[envs.default.matrix]]
python = ["2.7", "3.9"]

""",
    )

    write_file(
        repo_path / 'dummy',
        'pyproject.toml',
        """[project]
name = "dummy"
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: BSD License",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.9",
]
""",
    )

    write_file(
        repo_path / '.github' / 'workflows',
        'build-ddev.yml',
        """name: build ddev
env:
  APP_NAME: ddev
  PYTHON_VERSION: "3.9"
  PYOXIDIZER_VERSION: "0.24.0"
""",
    )

    write_file(
        repo_path / 'ddev',
        'pyproject.toml',
        """[tool.black]
target-version = ["py39"]

[tool.ruff]
target-version = "py39"
""",
    )

    write_file(
        repo_path
        / 'datadog_checks_dev'
        / 'datadog_checks'
        / 'dev'
        / 'tooling'
        / 'templates'
        / 'integration'
        / 'check'
        / '{check_name}',
        'pyproject.toml',
        """[project]
name = "dummy"
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: BSD License",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.9",
]
""",
    )

    yield repo


def write_file(folder, file, content):
    folder.mkdir(exist_ok=True, parents=True)
    file_path = folder / file
    file_path.write_text(content)
