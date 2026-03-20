# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.repo.core import Repository
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

    # Create fake Dockerfiles for Python upgrade tests
    # These are minimal versions with just the patterns the upgrade script looks for
    write_file(
        repo_path / '.builders' / 'images' / 'linux-aarch64',
        'Dockerfile',
        """ARG BASE_IMAGE=quay.io/pypa/manylinux2014_aarch64
FROM ${BASE_IMAGE}

# Compile and install Python 3
ENV PYTHON3_VERSION=3.13.7
RUN DOWNLOAD_URL="https://python.org/ftp/python/{{version}}/Python-{{version}}.tgz" \\
VERSION="${PYTHON3_VERSION}" \\
SHA256="c061fe2ed5209161ac32e55e570cf8fd84bcd05c0ebc80e6b86daa4f2d75b0ee" \\
RELATIVE_PATH="Python-{{version}}" \\
bash install-from-source.sh
""",
    )

    write_file(
        repo_path / '.builders' / 'images' / 'linux-x86_64',
        'Dockerfile',
        """ARG BASE_IMAGE=quay.io/pypa/manylinux2014_x86_64
FROM ${BASE_IMAGE}

# Compile and install Python 3
ENV PYTHON3_VERSION=3.13.7
RUN DOWNLOAD_URL="https://python.org/ftp/python/{{version}}/Python-{{version}}.tgz" \\
VERSION="${PYTHON3_VERSION}" \\
SHA256="c061fe2ed5209161ac32e55e570cf8fd84bcd05c0ebc80e6b86daa4f2d75b0ee" \\
RELATIVE_PATH="Python-{{version}}" \\
bash install-from-source.sh
""",
    )

    write_file(
        repo_path / '.builders' / 'images' / 'windows-x86_64',
        'Dockerfile',
        """FROM mcr.microsoft.com/windows/servercore:ltsc2022

ENV PYTHON_VERSION="3.13.7"
RUN Get-RemoteFile `
      -Uri https://www.python.org/ftp/python/$Env:PYTHON_VERSION/python-$Env:PYTHON_VERSION-amd64.exe `
      -Path python-$Env:PYTHON_VERSION-amd64.exe `
      -Hash 'b3dfdb2b9f43defb9c6c6d2dd679072dcc04e2c5d52ceaa4c0a001f39c3fa9a4'; `
    Start-Process -Wait python-$Env:PYTHON_VERSION-amd64.exe -ArgumentList '/quiet', 'InstallAllUsers=1'
""",
    )

    # Create fake macOS workflow file for Python upgrade tests
    # Uses Python Build Standalone (PBS) format
    write_file(
        repo_path / '.github' / 'workflows',
        'resolve-build-deps.yaml',
        """name: Resolve build dependencies

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - name: Set up Python
        env:
          PYTHON_PATCH: 7
          PBS_RELEASE: 20251202
          PBS_SHA256__aarch64: 799a3b76240496e4472dd60ed0cd5197e04637bea7fa16af68caeb989fadcb3a
          PBS_SHA256__x86_64: 705b39dd74490c3e9b4beb1c4f40bf802b50ba40fe085bdca635506a944d5e74
        run: |
          curl -fsSL -o pbs.tgz "https://github.com/astral-sh/python-build-standalone/releases/download/$PBS_RELEASE/cpython-$PYTHON_VERSION.$PYTHON_PATCH+$PBS_RELEASE-aarch64-apple-darwin-install_only_stripped.tar.gz"
""",
    )

    yield repo


def write_file(folder, file, content):
    folder.mkdir(exist_ok=True, parents=True)
    file_path = folder / file
    file_path.write_text(content)
