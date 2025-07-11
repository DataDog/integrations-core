# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from datadog_checks.dev.tooling.constants import set_root

from ddev.repo.core import Repository
from tests.helpers.api import write_file

FILES_IN_FAKE_REPO = [
    # Codeowners file
    (
        '.github',
        'CODEOWNERS',
        """
/dummy/                                 @DataDog/agent-integrations
/dummy2/                                 @DataDog/agent-integrations
""",
    ),
    # Ddev config file
    (
        '.ddev',
        'config.toml',
        """[overrides.validate.labeler]
include = ["datadog_checks_tests_helper"]
""",
    ),
    # Dummy manifest files
    ('dummy', 'manifest.json', """We don't need the content for this test, we just need the file"""),
    ('dummy2', 'manifest.json', """We don't need the content for this test, we just need the file"""),
    # Labeler config file
    (
        '.github/workflows/config',
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
    ),
]


def _fake_repo(tmp_path_factory, config_file, name, files_to_write):
    set_root('')  # for dcd compatibility running the tests
    repo_path = tmp_path_factory.mktemp(name)
    repo = Repository(name, str(repo_path))

    config_file.model.repos[name] = str(repo.path)
    config_file.model.repo = name
    config_file.save()
    for file_path, file_name, content in files_to_write:
        write_file(repo_path / file_path, file_name, content)

    return repo


@pytest.fixture
def fake_repo(
    request,
    tmp_path_factory,
    config_file,
    mocker,
):
    mocker.patch('ddev.utils.git.GitRepository.worktrees', return_value=[])

    yield _fake_repo(
        tmp_path_factory,
        config_file,
        'core',
        request.param if hasattr(request, 'param') else FILES_IN_FAKE_REPO,
    )


@pytest.fixture
def fake_extras_repo(
    request,
    tmp_path_factory,
    config_file,
    mocker,
):
    mocker.patch('ddev.utils.git.GitRepository.worktrees', return_value=[])
    yield _fake_repo(
        tmp_path_factory,
        config_file,
        'extras',
        request.param if hasattr(request, 'param') else FILES_IN_FAKE_REPO,
    )


@pytest.fixture
def fake_marketplace_repo(
    request,
    tmp_path_factory,
    config_file,
    mocker,
):
    mocker.patch('ddev.utils.git.GitRepository.worktrees', return_value=[])
    yield _fake_repo(
        tmp_path_factory,
        config_file,
        'marketplace',
        request.param if hasattr(request, 'param') else FILES_IN_FAKE_REPO,
    )
