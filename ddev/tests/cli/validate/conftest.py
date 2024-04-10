# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from datadog_checks.dev.tooling.constants import set_root

from ddev.repo.core import Repository


def _fake_repo(tmp_path_factory, config_file, name):
    set_root('')  # for dcd compatibility running the tests
    repo_path = tmp_path_factory.mktemp(name)
    repo = Repository(name, str(repo_path))

    config_file.model.repos[name] = str(repo.path)
    config_file.model.repo = name
    config_file.save()

    write_file(
        repo.path / '.github',
        'CODEOWNERS',
        """
/dummy/                                 @DataDog/agent-integrations
/dummy2/                                 @DataDog/agent-integrations
""",
    )

    write_file(
        repo_path / ".ddev",
        'config.toml',
        """[overrides.validate.labeler]
include = ["datadog_checks_tests_helper"]
""",
    )

    for integration in ('dummy', 'dummy2'):
        write_file(
            repo_path / integration,
            'manifest.json',
            """We don't need the content for this test, we just need the file""",
        )

    write_file(
        repo_path / '.github' / 'workflows' / 'config',
        'labeler.yml',
        """changelog/no-changelog:
- any:
  - requirements-agent-release.txt
  - '*/__about__.py'
- all:
  - '!*/datadog_checks/**'
  - '!*/pyproject.toml'
  - '!ddev/src/**'
integration/datadog_checks_tests_helper:
- datadog_checks_tests_helper/**/*
integration/dummy:
- dummy/**/*
integration/dummy2:
- dummy2/**/*
release:
- '*/__about__.py'
""",
    )

    return repo


@pytest.fixture
def fake_repo(
    tmp_path_factory,
    config_file,
):
    yield _fake_repo(tmp_path_factory, config_file, 'core')


@pytest.fixture
def fake_extras_repo(tmp_path_factory, config_file):
    yield _fake_repo(tmp_path_factory, config_file, 'extras')


@pytest.fixture
def fake_marketplace_repo(tmp_path_factory, config_file):
    yield _fake_repo(tmp_path_factory, config_file, 'marketplace')


def write_file(folder, file, content):
    folder.mkdir(exist_ok=True, parents=True)
    file_path = folder / file
    file_path.write_text(content)
