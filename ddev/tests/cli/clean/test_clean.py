# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def test_clean_successful(ddev, repository):
    artifact = repository.path / 'build' / 'something.txt'
    artifact.parent.mkdir()
    artifact.touch()

    result = ddev('clean')

    assert result.exit_code == 0, result.output
    assert not artifact.is_file()
