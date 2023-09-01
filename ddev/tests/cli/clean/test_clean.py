# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def test_clean_successful(ddev, repository):
    artifact_remove = repository.path / 'build' / 'something.txt'
    artifact_remove.parent.mkdir()
    artifact_remove.touch()

    artifact_keep = repository.path / '.vscode' / 'something2.txt'
    artifact_keep.parent.mkdir()
    artifact_keep.touch()

    result = ddev('clean')

    assert result.exit_code == 0, result.output
    assert not artifact_remove.is_file()
    assert artifact_keep.is_file()
