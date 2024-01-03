# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.repo.core import Repository

OLD_PYTHON_VERSION = "3.11"
NEW_PYTHON_VERSION = "3.12"


@pytest.fixture
def fake_repo(tmp_path_factory, config_file, ddev):
    repo_path = tmp_path_factory.mktemp('integrations-core')
    repo = Repository('integrations-core', str(repo_path))

    config_file.model.repos['core'] = str(repo.path)
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
""",
    )

    write_file(
        repo_path / 'dummy',
        'hatch.toml',
        f"""[env.collectors.datadog-checks]

[[envs.default.matrix]]
python = ["2.7", "{OLD_PYTHON_VERSION}"]

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
        "Programming Language :: Python :: 2.7",
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
        "Programming Language :: Python :: 2.7",
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
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: {OLD_PYTHON_VERSION}",
]
""",
    )

    yield repo


def write_file(folder, file, content):
    folder.mkdir(exist_ok=True, parents=True)
    file_path = folder / file
    file_path.write_text(content)
