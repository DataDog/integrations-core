# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

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


def test_multiple_invalid_third_party_integrations(fake_repo, ddev):
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

    result = ddev('validate', 'dep', 'bad_check_2')
    result_2 = ddev('validate', 'dep', 'bad_check_3')
    assert result.exit_code == 1
    assert error_regex.search(result.output), f"Unexpected output: {result.output}"
    assert result_2.exit_code == 1
    assert error_regex.search(result_2.output), f"Unexpected output: {result_2.output}"


def test_one_valid_one_invalid_integration(fake_repo, ddev):
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

    result = ddev('validate', 'dep', 'valid_check_2')
    result_2 = ddev('validate', 'dep', 'bad_check_4')
    assert result.exit_code == 0
    assert match_regex.match(result.output), f"Unexpected output: {result.output}"
    assert result_2.exit_code == 1
    assert error_regex.search(result_2.output), f"Unexpected output: {result_2.output}"


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


def test_validate_dep_core_path(fake_integrations_core_repo, ddev):
    assert 'integrations-core' in str(fake_integrations_core_repo.path)
    _write_git_dep_check(fake_integrations_core_repo.path, 'git_dep_check')
    result = ddev('validate', 'dep', 'git_dep_check')
    assert result.exit_code == 0
    assert match_regex.match(result.output), f"Unexpected output: {result.output}"


def test_validate_dep_non_core_path(fake_repo, ddev):
    assert 'integrations-core' not in str(fake_repo.path)
    _write_git_dep_check(fake_repo.path, 'git_dep_check')
    result = ddev('validate', 'dep', 'git_dep_check')
    assert result.exit_code == 0
    assert match_regex.match(result.output), f"Unexpected output: {result.output}"
