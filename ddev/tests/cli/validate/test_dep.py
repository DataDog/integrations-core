# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import pytest

from tests.helpers.api import write_file

error_regex = re.compile(r"(?s)^\s*[A-Za-z0-9_\/.-]+\.toml has the following errors:\n(?:  - .+\n)+")
match_regex = re.compile(r"^\s*All dependencies are valid!\s*$")


def test_valid_integration(fake_repo, ddev):
    write_file(
        fake_repo.path / 'valid_check',
        'pyproject.toml',
        """
        [project]
        dependencies = [
            "datadog-checks-base>=37.21.0",
        ]
        """,
    )
    result = ddev('validate', 'dep', 'valid_check')
    assert result.exit_code == 0
    assert match_regex.match(result.output), f"Unexpected output: {result.output}"


def test_invalid_third_party_integration(fake_repo, ddev):
    write_file(
        fake_repo.path / 'bad_check',
        'pyproject.toml',
        """
        [project]
        dependencies = [
        "datadog-checks-base>=37.21.0",
        "dep-d==1.5.0",
        ]
        """,
    )
    result = ddev('validate', 'dep', 'bad_check')
    assert result.exit_code == 1
    assert error_regex.search(result.output), f"Unexpected output: {result.output}"


@pytest.mark.parametrize('check_name', ['bad_check_2', 'bad_check_3'])
def test_multiple_invalid_third_party_integrations(fake_repo, ddev, check_name):
    write_file(
        fake_repo.path / 'bad_check_2',
        'pyproject.toml',
        """
        [project]
        dependencies = [
        "dep-b==1.5.0",
        "dep-e==1.5.0",
        ]
        """,
    )

    write_file(
        fake_repo.path / 'bad_check_3',
        'pyproject.toml',
        """
        [project]
        dependencies = [
        "datadog-checks-base>=37.21.0",
        "dep-f==1.5.0",
        ]
        """,
    )

    result = ddev('validate', 'dep', check_name)
    assert result.exit_code == 1
    assert error_regex.search(result.output), f"Unexpected output: {result.output}"


@pytest.mark.parametrize('check_name', ['valid_check_2', 'bad_check_4'])
def test_one_valid_one_invalid_integration(fake_repo, ddev, check_name):
    write_file(
        fake_repo.path / 'valid_check_2',
        'pyproject.toml',
        """
        [project]
        dependencies = [
        "datadog-checks-base>=37.21.0",
        ]
        """,
    )

    write_file(
        fake_repo.path / 'bad_check_4',
        'pyproject.toml',
        """
        [project]
        dependencies = [
        "datadog-checks-base>=37.21.0",
        "dep-f==1.5.0",
        ]
        """,
    )

    result = ddev('validate', 'dep', check_name)
    if check_name == 'valid_check_2':
        assert result.exit_code == 0
        assert match_regex.match(result.output), f"Unexpected output: {result.output}"
    else:
        assert result.exit_code == 1
        assert error_regex.search(result.output), f"Unexpected output: {result.output}"


UNPINNED_OPT_CHECK = 'unpinned_opt_check'

UNPINNED_OPTIONAL_DEP = 'acme-unpinned-lib'
PYPROJECT_UNPINNED_OPTIONAL = f"""
        [project]
        dependencies = [
            "datadog-checks-base>=37.21.0",
        ]

        [project.optional-dependencies]
        libs = [
            "{UNPINNED_OPTIONAL_DEP}",
        ]
        """


def _write_git_dep_check(repo_path, check_name: str) -> None:
    git_dep = 'sample_git_pkg @ git+https://github.com/pypa/pip.git@24.0'
    write_file(
        repo_path,
        'agent_requirements.in',
        f"""datadog-checks-base==37.21.0
{git_dep}
""",
    )
    write_file(
        repo_path / check_name,
        'pyproject.toml',
        f"""
        [project]
        dependencies = [
            "datadog-checks-base>=37.21.0",
        ]

        [project.optional-dependencies]
        libs = [
            "{git_dep}",
        ]
        """,
    )


def test_core_rejects_unpinned_optional_dependency(fake_repo, ddev):
    """With `-c`, unpinned PyPI deps under optional-dependencies fail validation."""
    write_file(
        fake_repo.path,
        'agent_requirements.in',
        f"""datadog-checks-base==37.21.0
{UNPINNED_OPTIONAL_DEP}==1.0.0
""",
    )
    write_file(fake_repo.path, f'{UNPINNED_OPT_CHECK}/pyproject.toml', PYPROJECT_UNPINNED_OPTIONAL)
    result = ddev('-c', 'validate', 'dep', UNPINNED_OPT_CHECK)
    assert result.exit_code == 1
    assert 'Unpinned version' in result.output


def test_core_rejects_unpinned_optional_dependency_default_repo(fake_repo, ddev):
    """Default repo is core: unpinned optional PyPI deps fail without passing `-c`."""
    write_file(
        fake_repo.path,
        'agent_requirements.in',
        f"""datadog-checks-base==37.21.0
{UNPINNED_OPTIONAL_DEP}==1.0.0
""",
    )
    write_file(fake_repo.path, f'{UNPINNED_OPT_CHECK}/pyproject.toml', PYPROJECT_UNPINNED_OPTIONAL)
    result = ddev('validate', 'dep', UNPINNED_OPT_CHECK)
    assert result.exit_code == 1
    assert 'Unpinned version' in result.output


@pytest.mark.parametrize(
    'repo_fixture, flag',
    [
        pytest.param('fake_extras_repo', '-e', id='extras'),
        pytest.param('fake_marketplace_repo', '-m', id='marketplace'),
    ],
)
def test_non_core_repo_allows_unpinned_optional_dependency(repo_fixture, flag, ddev, request):
    """Non-core repos allow unpinned optional PyPI deps (no integrations-core pin rules)."""
    repo = request.getfixturevalue(repo_fixture)
    write_file(
        repo.path,
        'agent_requirements.in',
        """datadog-checks-base>=37.21.0
""",
    )
    write_file(repo.path, f'{UNPINNED_OPT_CHECK}/pyproject.toml', PYPROJECT_UNPINNED_OPTIONAL)
    result = ddev(flag, 'validate', 'dep', UNPINNED_OPT_CHECK)
    assert result.exit_code == 0, result.output
    assert 'Unpinned version' not in result.output
    assert match_regex.match(result.output), f"Unexpected output: {result.output}"


def test_validate_dep_git_url_succeeds_on_core(fake_repo, ddev):
    """Git URL deps return early from verify_dependency and are not treated as unpinned PyPI."""
    _write_git_dep_check(fake_repo.path, 'git_dep_check')
    result = ddev('-c', 'validate', 'dep', 'git_dep_check')
    assert result.exit_code == 0
    assert 'Unpinned version' not in result.output
    assert match_regex.match(result.output), f"Unexpected output: {result.output}"
