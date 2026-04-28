# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess

import pytest
from pytest_mock import MockerFixture

from ddev.utils.fs import Path
from tests.cli.release.conftest import reset_fragments_dir
from tests.helpers.git import ClonedRepo
from tests.helpers.runner import CliRunner


@pytest.fixture
def build_fragments(repo_with_towncrier: ClonedRepo) -> Path:
    fragments_dir = reset_fragments_dir(repo_with_towncrier.path / 'ddev' / 'changelog.d')
    (fragments_dir / '1.added').write_text('Foo')
    (fragments_dir / '2.fixed').write_text('Bar')
    return fragments_dir


def test_prints_changelog_to_stdout(ddev: CliRunner, build_fragments: Path, helpers):
    result = ddev('release', 'changelog', 'draft', 'ddev')

    assert result.exit_code == 0, result.output
    output = helpers.remove_trailing_spaces(result.output)
    assert '***Added***:' in output
    assert '* Foo ([#1](https://github.com/DataDog/integrations-core/pull/1))' in output
    assert '***Fixed***:' in output
    assert '* Bar ([#2](https://github.com/DataDog/integrations-core/pull/2))' in output
    # Fragments are preserved (draft mode doesn't remove them).
    assert (build_fragments / '1.added').exists()
    assert (build_fragments / '2.fixed').exists()


def test_writes_to_file(ddev: CliRunner, build_fragments: Path, tmp_path: Path, helpers):
    output_file = tmp_path / 'preview.md'

    result = ddev('release', 'changelog', 'draft', 'ddev', '--file', str(output_file))

    assert result.exit_code == 0, result.output
    assert f'Wrote changelog preview to {output_file}' in result.output
    contents = helpers.remove_trailing_spaces(output_file.read_text())
    assert '* Foo ([#1](https://github.com/DataDog/integrations-core/pull/1))' in contents
    assert '* Bar ([#2](https://github.com/DataDog/integrations-core/pull/2))' in contents


def test_multiple_targets_prefixed_with_target_name(ddev: CliRunner, repo_with_towncrier: ClonedRepo, helpers):
    for target in ('ddev', 'datadog_checks_dev'):
        fragments_dir = reset_fragments_dir(repo_with_towncrier.path / target / 'changelog.d')
        (fragments_dir / '1.added').write_text(f'Entry for {target}')

    result = ddev('release', 'changelog', 'draft', 'ddev', 'datadog_checks_dev')

    assert result.exit_code == 0, result.output
    output = helpers.remove_trailing_spaces(result.output)
    assert '# ddev' in output
    assert '# datadog_checks_dev' in output
    assert 'Entry for ddev' in output
    assert 'Entry for datadog_checks_dev' in output


@pytest.mark.parametrize(
    'args, expected_message',
    [
        pytest.param(
            ['definitely_not_an_integration'], 'Unknown target: definitely_not_an_integration', id='one_unknown'
        ),
        pytest.param(
            ['definitely_not_an_integration', 'also_missing'],
            'Unknown targets: definitely_not_an_integration, also_missing',
            id='multiple_unknown',
        ),
        pytest.param([], "Missing argument 'TARGETS...'", id='no_targets'),
    ],
)
def test_argument_errors(ddev: CliRunner, repo_with_towncrier: ClonedRepo, args: list[str], expected_message: str):
    result = ddev('release', 'changelog', 'draft', *args)

    assert result.exit_code != 0
    assert expected_message in result.output


def test_no_fragments_renders_no_significant_changes(ddev: CliRunner, repo_with_towncrier: ClonedRepo):
    reset_fragments_dir(repo_with_towncrier.path / 'ddev' / 'changelog.d')

    result = ddev('release', 'changelog', 'draft', 'ddev')

    assert result.exit_code == 0, result.output
    assert 'No significant changes' in result.output


def test_surfaces_towncrier_failure(ddev: CliRunner, build_fragments: Path, mocker: MockerFixture):
    mocker.patch(
        'ddev.utils.platform.Platform.run_command',
        return_value=subprocess.CompletedProcess(args=[], returncode=1, stdout='partial output', stderr='boom'),
    )

    result = ddev('release', 'changelog', 'draft', 'ddev')

    assert result.exit_code != 0
    assert 'partial output' in result.output
    assert 'towncrier build exited with code 1' in result.output
    assert 'boom' in result.output
