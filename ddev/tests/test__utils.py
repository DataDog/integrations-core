# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# This file is named with a double underscore so it comes first lexicographically


def test_cloned_repo(repository, local_repo):
    integrations = sorted(
        entry.name for entry in repository.path.iterdir() if (repository.path / entry.name / 'manifest.json').is_file()
    )
    expected_integrations = sorted(
        entry.name for entry in local_repo.iterdir() if (local_repo / entry.name / 'manifest.json').is_file()
    )

    # Note: We are checking that the number of integrations is +- 1 from the `master`
    # branch as a workaround for scenarios where the current branch adds/removes
    # an integration and there has a different integration count than master.
    if len(integrations) != len(expected_integrations):
        assert abs(len(integrations) - len(expected_integrations)) == 1
    else:
        assert integrations == expected_integrations
