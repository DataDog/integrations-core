# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest
from ddev.utils.structures import EnvVars


@pytest.fixture(scope='module', autouse=True)
def terminal_width():
    with EnvVars({'COLUMNS': '200'}):
        yield


def test_no_dd_url(ddev, repository, helpers, config_file):
    config_file.model.orgs['default']['dd_url'] = ''
    config_file.save()

    result = ddev('validate', 'manifest', 'disk')

    assert result.exit_code == 1, result.output
    assert result.output == helpers.dedent(
        """
        No `dd_url` has been set for org `default`
        """
    )


def test_error_single_integration(ddev, repository, helpers, network_replay):
    network_replay('manifest/missing_app_uuid.yaml', record_mode='none')

    check = 'mongo'
    manifest_file = repository.path / check / 'manifest.json'
    manifest = json.loads(manifest_file.read_text())
    del manifest['app_uuid']
    manifest_file.write_text(json.dumps(manifest))

    result = ddev('validate', 'manifest', check)

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        Manifests
        └── MongoDB
            └── manifest.json

                API input validation failed: {'app_uuid': [u'Missing data for required field.']}

        Errors: 1
        """
    )


def test_error_multiple_integrations(ddev, repository, helpers, network_replay):
    network_replay('manifest/missing_app_uuid.yaml', record_mode='none')

    for check in ('mongo', 'vsphere'):
        manifest_file = repository.path / check / 'manifest.json'
        manifest = json.loads(manifest_file.read_text())
        del manifest['app_uuid']
        manifest_file.write_text(json.dumps(manifest))

    result = ddev('validate', 'manifest')

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        Manifests
        ├── MongoDB
        │   └── manifest.json
        │
        │       API input validation failed: {'app_uuid': [u'Missing data for required field.']}
        └── vSphere
            └── manifest.json

                API input validation failed: {'app_uuid': [u'Missing data for required field.']}

        Errors: 2
        """
    )


def test_passing(ddev, repository, helpers, network_replay):
    network_replay('manifest/success.yaml', record_mode='none')

    result = ddev('validate', 'manifest', 'postgres')

    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        Validating manifest.json files for 1 checks ...
        Manifests

        Passed: 1
        """
    )
