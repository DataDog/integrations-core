# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .conftest import write_file


def test_codeowners_integrations_core(fake_repo, ddev):
    result = ddev('validate', 'codeowners')
    assert result.exit_code == 0, result.output


def test_codeowners_valid(fake_extras_repo, ddev):
    result = ddev('-e', 'validate', 'codeowners')
    assert result.exit_code == 0, result.output


def test_codeowners_invalid(fake_extras_repo, ddev):
    write_file(
        fake_extras_repo.path / '.github',
        'CODEOWNERS',
        """
/dummy/                                 @DataDog/agent-integrations
""",
    )
    result = ddev('-e', 'validate', 'codeowners')
    assert result.exit_code == 1, result.output
    assert "Integration dummy2 does not have a valid `CODEOWNERS` entry." in result.output
