# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest

from tests.helpers.api import write_file

MANIFEST = json.dumps(
    {
        "manifest_version": "2.0.0",
        "app_uuid": "f84d2d4e-03c5-44d7-aa9e-53efc08346a7",
        "app_id": "my-check",
        "display_on_public_website": False,
        "tile": {
            "overview": "README.md#Overview",
            "configuration": "README.md#Setup",
            "support": "README.md#Support",
            "changelog": "CHANGELOG.md",
            "description": "",
            "title": "My Check",
            "media": [],
            "classifier_tags": ["Supported OS::Linux"],
        },
        "assets": {
            "integration": {
                "source_type_name": "My_Check",
                "configuration": {"spec": "assets/configuration/spec.yaml"},
                "events": {"creates_events": False},
                "metrics": {"prefix": "my_check.", "check": "", "metadata_path": "metadata.csv"},
            }
        },
        "author": {
            "support_email": "help@datadoghq.com",
            "name": "Datadog",
            "homepage": "https://www.datadoghq.com",
            "sales_email": "info@datadoghq.com",
        },
    }
)

SPEC_YAML = """\
name: My Check
files:
- name: my_check.yaml
  options:
  - template: init_config
    options:
    - template: init_config/default
  - template: instances
    options:
    - template: instances/default
"""

PYPROJECT = """\
[project]
name = "datadog-my-check"
"""

ABOUT = '__version__ = "1.0.0"\n'


def _write_check(repo_path, *, with_spec: bool = True, with_example: bool = False):
    write_file(repo_path / 'my_check', 'manifest.json', MANIFEST)
    write_file(repo_path / 'my_check', 'pyproject.toml', PYPROJECT)
    write_file(repo_path / 'my_check/datadog_checks/my_check', '__about__.py', ABOUT)
    if with_spec:
        write_file(repo_path / 'my_check/assets/configuration', 'spec.yaml', SPEC_YAML)
    if with_example:
        # Use a non-standard filename so the legacy YAML validator doesn't pick it up
        write_file(repo_path / 'my_check/datadog_checks/my_check/data', 'conf.example.yaml', '# placeholder\n')


@pytest.mark.parametrize(
    'repo_fixture, expect_failure',
    [
        ('fake_repo', True),
        ('fake_extras_repo', False),
        ('fake_marketplace_repo', False),
    ],
)
def test_missing_spec_with_example_file(repo_fixture, expect_failure, request, ddev):
    """When a check has a data/example file but no spec, core must fail; extras/marketplace warn but pass."""
    fake_repo = request.getfixturevalue(repo_fixture)
    _write_check(fake_repo.path, with_spec=False, with_example=True)

    result = ddev('validate', 'config', 'my_check')

    assert 'Validating default configuration files for 1 checks...' in result.output
    assert 'my_check:' in result.output
    assert 'Did not find spec file' in result.output
    if expect_failure:
        assert result.exit_code == 1
        assert 'Files with errors: 1' in result.output
    else:
        assert result.exit_code == 0


@pytest.mark.parametrize(
    'check',
    ['ddev', 'datadog_checks_dev', 'datadog_checks_base', 'datadog_checks_dependency_provider', 'datadog_checks_downloader'],
)
def test_configless_check_is_skipped(check, fake_repo, ddev):
    """Checks that do not ship Agent configuration are skipped."""
    result = ddev('validate', 'config', check)
    assert result.exit_code == 0
    assert f'Skipping {check}, it does not need an Agent-level config.' in result.output


def test_valid_spec_renders_example(fake_repo, ddev):
    """A valid spec generates a rendered example file when run with --sync, and validates afterwards."""
    _write_check(fake_repo.path, with_spec=True)

    sync_result = ddev('validate', 'config', 'my_check', '--sync')
    assert sync_result.exit_code == 0
    assert 'Writing config file to' in sync_result.output

    validate_result = ddev('validate', 'config', 'my_check')
    assert validate_result.exit_code == 0
    assert 'configuration files are valid' in validate_result.output


def test_out_of_sync_example_file_fails(fake_repo, ddev):
    """An out-of-sync rendered example file should fail validation."""
    _write_check(fake_repo.path, with_spec=True)

    # First render once, then mutate the rendered file so it goes out of sync.
    sync_result = ddev('validate', 'config', 'my_check', '--sync')
    assert sync_result.exit_code == 0

    example_path = fake_repo.path / 'my_check' / 'datadog_checks' / 'my_check' / 'data' / 'conf.yaml.example'
    example_path.write_text('# tampered\n')

    result = ddev('validate', 'config', 'my_check')
    assert result.exit_code == 1
    assert 'is not in sync' in result.output
    assert 'Files with errors:' in result.output
