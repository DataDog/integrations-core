# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from ddev.utils.toml import dump_toml_data, load_toml_file


@pytest.mark.parametrize(
    "name, contents, expected_output",
    [
        pytest.param(
            "explicit_licenses",
            {'dummy_package': 'dummy_license'},
            """
                EXPLICIT_LICENSES contains additional package not in agent requirements:
                dummy_package
            """,
            id="explicit licenses",
        ),
        pytest.param(
            "package_repo_overrides",
            {'dummy_package': 'https://github.com/dummy_package'},
            """
                PACKAGE_REPO_OVERRIDES contains additional package not in agent
                requirements: dummy_package
            """,
            id="package repo overrides",
        ),
    ],
)
def test_error_extra_dependency(name, contents, expected_output, ddev, repository, network_replay, helpers):
    network_replay('fixtures/network/license/extra_dependency.yaml', record_mode='none')
    config_file = repository.path / '.ddev' / 'config.toml'
    data = load_toml_file(config_file)
    data['overrides'][name] = contents

    dump_toml_data(data, config_file)

    result = ddev('validate', 'licenses')

    assert result.exit_code == 1, result.output

    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        f"""
        Licenses
        └── {name.upper()}
            └── dummy_package
                {expected_output}
        Errors: 1
        """
    )
