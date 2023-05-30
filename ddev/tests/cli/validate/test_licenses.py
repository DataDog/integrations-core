# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Tests:
# If extra dep in EXPLICIT_LICENSES not in agent_requirements.in, then fail
# If extra dep in PACKAGE_REPO_OVERRIDES not in agent_requirements.in, then fail
# If all EXPLICIT_LICENSES and PACKAGE_REPO_OVERRIDES deps are in agent_requirements.in, then pass


def test_error_extra_dependency(ddev, helpers, network_replay):
    network_replay('fixtures/network/license/missing_app_uuid.yaml', record_mode='none')

    # TODO: Figure out testing of modules

    # with mock.patch("ddev.src.ddev.cli.validate.test_constant.EXPLICIT_LICENSES",
    #     return_value=mocked_explicit_licenses):

    #     result = ddev('validate', 'licenses')

    # assert result.exit_code == 1, result.output
