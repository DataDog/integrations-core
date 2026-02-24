# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.mark.parametrize('use_here', [True, False])
def test_validate_models_preserves_core_license_headers(ddev, repository_as_cwd, use_here):
    args = ['validate', 'models', 'zk', '-s']
    if use_here:
        args = ['--here'] + args

    result = ddev(*args)

    assert result.exit_code == 0, result.output
    assert 'All 5 data model files are in sync!' in result.output

    instance = (
        repository_as_cwd.path / 'zk' / 'datadog_checks' / 'zk' / 'config_models' / 'instance.py'
    ).read_text()
    assert instance.startswith('# (C) Datadog, Inc.')
