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

    assert integrations == expected_integrations
