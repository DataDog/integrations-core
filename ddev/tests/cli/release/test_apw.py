# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import subprocess
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from ddev.release.apw import Release
from tests.helpers.runner import CliRunner


@pytest.mark.parametrize(
    'repository',
    [
        'DataDog/integrations-core',
        'DataDog/integrations-extras',
        'DataDog/marketplace',
        'ddoghq/publishing-platform',
        'ddoghq/integrations-internal-core',
    ],
)
def test_package_arbitrary_asset_checkout(
    ddev: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repository: str
):
    # Pubplat has no integration metadata or named ddev repository configuration.
    source = tmp_path / 'checkout'
    source.mkdir()
    subprocess.run(['git', 'init', '--quiet', str(source)], check=True)
    (source / 'future-assets').mkdir()
    (source / 'future-assets/example.json').write_text('{}')
    subprocess.run(['git', '-C', str(source), 'add', '.'], check=True)
    subprocess.run(
        [
            'git',
            '-C',
            str(source),
            '-c',
            'user.name=Test',
            '-c',
            'user.email=test@example.invalid',
            '-c',
            'commit.gpgSign=false',
            '-c',
            'core.hooksPath=/dev/null',
            'commit',
            '--quiet',
            '-m',
            'Fixture',
        ],
        check=True,
    )
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    monkeypatch.chdir(source)
    monkeypatch.setenv('GH_REPO', 'wrong/implicit-repository')
    result = ddev('--here', 'release', 'apw', 'package', '--repository', repository, '--commit', commit)
    assert result.exit_code == 0, result.output
    metadata = json.loads((source / 'dist/release.json').read_text())
    assert metadata['repository'] == repository
    assert metadata['commit'] == commit
    assert (source / 'dist/apw-assets.tar.gz').is_file()


@pytest.mark.parametrize('needed', [False, True])
def test_check_exports_workflow_output_and_summary(
    ddev: CliRunner, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch, step_summary: Path, needed: bool
):
    def check(release: Release) -> bool:
        assert release.repository == 'ddoghq/publishing-platform'
        assert release.commit == 'a' * 40
        return needed

    monkeypatch.setenv('GH_REPO', 'ddoghq/publishing-platform')
    mocker.patch.object(Release, 'needs_package', autospec=True, side_effect=check)
    result = ddev('release', 'apw', 'check', '--commit', 'a' * 40)
    assert result.exit_code == 0, result.output
    assert f'package={str(needed).lower()}' in result.output
    assert ('Packaging needed.' if needed else 'Complete release exists; skipping') in step_summary.read_text()


def test_publish_uses_selected_directory(ddev: CliRunner, mocker: MockerFixture, tmp_path: Path, step_summary: Path):
    def publish(release: Release, directory: Path) -> str:
        assert release.repository == 'ddoghq/integrations-internal-core'
        assert release.commit == 'b' * 40
        assert directory == tmp_path
        return 'Published verified APW snapshot.'

    mocker.patch.object(Release, 'publish', autospec=True, side_effect=publish)
    result = ddev(
        'release',
        'apw',
        'publish',
        '--repository',
        'ddoghq/integrations-internal-core',
        '--commit',
        'b' * 40,
        '--directory',
        str(tmp_path),
    )
    assert result.exit_code == 0, result.output
    assert 'Published verified APW snapshot.' in step_summary.read_text()


def test_tag_is_separate_from_publication(ddev: CliRunner, mocker: MockerFixture, step_summary: Path):
    def tag(release: Release) -> str:
        assert release.repository == 'DataDog/integrations-core'
        assert release.commit == 'a' * 40
        return 'Created source tag at the expected commit.'

    mocker.patch.object(Release, 'ensure_tag', autospec=True, side_effect=tag)
    result = ddev('release', 'apw', 'tag', '--repository', 'DataDog/integrations-core', '--commit', 'a' * 40)
    assert result.exit_code == 0, result.output
    assert 'Created source tag at the expected commit.' in step_summary.read_text()
