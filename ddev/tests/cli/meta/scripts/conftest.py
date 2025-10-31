# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import shutil

import pytest

from ddev.repo.core import Repository
from ddev.utils.fs import Path
from ddev.utils.git import GitRepository

# Whenenever we bump python version, we also need to bump the python
# version in the conftest.py.
OLD_PYTHON_VERSION = "3.13"
NEW_PYTHON_VERSION = "3.14"


@pytest.fixture
def fake_repo(tmp_path_factory, config_file, local_repo, ddev, mocker):
    repo_path = tmp_path_factory.mktemp('integrations-core')
    repo = Repository('integrations-core', str(repo_path))

    mocker.patch.object(GitRepository, 'worktrees', return_value=[])

    config_file.model.repos["core"] = str(repo.path)
    config_file.save()

    write_file(
        repo_path / 'ddev' / 'src' / 'ddev' / 'repo',
        'constants.py',
        f"""# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
CONFIG_DIRECTORY = '.ddev'
NOT_SHIPPABLE = frozenset(['datadog_checks_dev', 'datadog_checks_tests_helper', 'ddev'])
FULL_NAMES = {{
    'core': 'integrations-core',
    'extras': 'integrations-extras',
    'marketplace': 'marketplace',
    'agent': 'datadog-agent',
}}

# This is automatically maintained
PYTHON_VERSION = '{OLD_PYTHON_VERSION}'
PYTHON_VERSION_FULL = '3.13.7'
""",
    )

    write_file(
        repo_path / 'dummy',
        'hatch.toml',
        f"""[env.collectors.datadog-checks]

[[envs.default.matrix]]
python = ["{OLD_PYTHON_VERSION}"]

""",
    )

    write_file(
        repo_path / 'dummy',
        'metadata.csv',
        """metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric
dummy.metric,gauge,,,,description,0,dummy,,""",
    )

    for integration in ('dummy', 'datadog_checks_dependency_provider'):
        write_file(
            repo_path / integration,
            'pyproject.toml',
            f"""[project]
    name = "dummy"
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: {OLD_PYTHON_VERSION}",
    ]
    """,
        )

    write_file(
        repo_path / 'logs_only',
        'pyproject.toml',
        f"""[project]
    name = "dummy"
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: {OLD_PYTHON_VERSION}",
    ]
    """,
    )

    write_file(
        repo_path / '.github' / 'workflows',
        'build-ddev.yml',
        f"""name: build ddev
env:
  APP_NAME: ddev
  PYTHON_VERSION: "{OLD_PYTHON_VERSION}"
  PYOXIDIZER_VERSION: "0.24.0"
""",
    )

    write_file(
        repo_path / 'ddev',
        'pyproject.toml',
        f"""[tool.black]
target-version = ["py{OLD_PYTHON_VERSION.replace('.', '')}"]

[tool.ruff]
target-version = "py{OLD_PYTHON_VERSION.replace('.', '')}"
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
        f"""[project]
name = "dummy"
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: BSD License",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: {OLD_PYTHON_VERSION}",
]
""",
    )

    # Copy actual Dockerfiles from the real repository for Python upgrade tests
    dockerfiles_to_copy = [
        '.builders/images/linux-aarch64/Dockerfile',
        '.builders/images/linux-x86_64/Dockerfile',
        '.builders/images/windows-x86_64/Dockerfile',
    ]

    for dockerfile_path in dockerfiles_to_copy:
        source = Path(local_repo) / dockerfile_path
        dest = repo_path / dockerfile_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)

    # Copy actual macOS workflow file for Python upgrade tests
    workflow_source = Path(local_repo) / '.github' / 'workflows' / 'resolve-build-deps.yaml'
    workflow_dest = repo_path / '.github' / 'workflows' / 'resolve-build-deps.yaml'
    workflow_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(workflow_source, workflow_dest)

    yield repo


def write_file(folder, file, content):
    folder.mkdir(exist_ok=True, parents=True)
    file_path = folder / file
    file_path.write_text(content)
