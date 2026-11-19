# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from apw_assets import Release, main


@pytest.fixture
def step_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / 'step-summary.md'
    path.touch()
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(path))
    return path


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
def test_package_arbitrary_asset_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repository: str):
    # Asset repositories need no integration metadata or ddev repository configuration.
    source = tmp_path / 'checkout'
    source.mkdir()
    subprocess.run(['git', 'init', '--quiet', str(source)], check=True)
    (source / 'future-assets').mkdir()
    (source / 'future-assets/example.json').write_text('{}')
    (source / '-vendor').mkdir()
    (source / '-vendor/dependency.bin').write_bytes(b'excluded')
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
    # Execute the action's actual shell so option binding is covered at its boundary.
    action_dir = Path(__file__).resolve().parents[1]
    action = yaml.safe_load((action_dir / 'action.yml').read_text())
    package_step = next(step for step in action['runs']['steps'] if step.get('id') == 'package')
    subprocess.run(
        ['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', package_step['run']],
        check=True,
        env={
            **os.environ,
            'PATH': str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH'],
            'GITHUB_ACTION_PATH': str(action_dir),
            'GITHUB_REPOSITORY': repository,
            'GITHUB_SHA': commit,
            'APW_DIRECTORY': '-dist',
            'APW_EXCLUDE': '-vendor/**',
        },
    )
    metadata = json.loads((source / '-dist/release.json').read_text())
    assert metadata['repository'] == repository
    assert metadata['commit'] == commit
    with tarfile.open(source / '-dist/apw-assets.tar.gz') as archive:
        assert {member.name for member in archive if member.isfile()} == {'repo/future-assets/example.json'}


@pytest.mark.parametrize('needed', [False, True])
def test_check_exports_workflow_output_and_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], step_summary: Path, needed: bool
):
    def check(release: Release) -> bool:
        assert release.repository == 'ddoghq/publishing-platform'
        assert release.commit == 'a' * 40
        return needed

    monkeypatch.setenv('GH_REPO', 'ddoghq/publishing-platform')
    with patch.object(Release, 'needs_package', autospec=True, side_effect=check):
        assert main(['check', '--commit', 'a' * 40]) == 0
    assert capsys.readouterr().out == f'package={str(needed).lower()}\n'
    assert ('Packaging needed.' if needed else 'Complete release exists; skipping') in step_summary.read_text()


def test_publish_uses_selected_directory(tmp_path: Path, step_summary: Path):
    def publish(release: Release, directory: Path) -> str:
        assert release.repository == 'ddoghq/integrations-internal-core'
        assert release.commit == 'b' * 40
        assert directory == tmp_path
        return 'Published verified APW snapshot.'

    with patch.object(Release, 'publish', autospec=True, side_effect=publish):
        args = ['publish', '--repository', 'ddoghq/integrations-internal-core', '--commit', 'b' * 40]
        assert main([*args, '--directory', str(tmp_path)]) == 0
    assert 'Published verified APW snapshot.' in step_summary.read_text()


def test_tag_is_separate_from_publication(step_summary: Path):
    def tag(release: Release) -> str:
        assert release.repository == 'DataDog/integrations-core'
        assert release.commit == 'a' * 40
        return 'Created source tag at the expected commit.'

    with patch.object(Release, 'ensure_tag', autospec=True, side_effect=tag):
        assert main(['tag', '--repository', 'DataDog/integrations-core', '--commit', 'a' * 40]) == 0
    assert 'Created source tag at the expected commit.' in step_summary.read_text()


@pytest.mark.parametrize('dry_run', [False, True])
def test_cleanup_options_and_summary(step_summary: Path, dry_run: bool):
    with patch.object(Release, 'cleanup', autospec=True, return_value='Cleanup completed.') as cleanup:
        args = ['cleanup', '--repository', 'DataDog/marketplace', '--commit', 'c' * 40, '--retention-days', '7']
        assert main([*args, *(['--dry-run'] if dry_run else [])]) == 0
    release = cleanup.call_args.args[0]
    assert release.repository == 'DataDog/marketplace'
    assert release.commit == 'c' * 40
    cleanup.assert_called_once_with(release, 7, dry_run=dry_run)
    assert 'Cleanup completed.' in step_summary.read_text()


@pytest.mark.parametrize(
    'args',
    [
        ['check', '--repository', 'DataDog/marketplace', '--commit', 'a' * 40, '--exclude', 'vendor/**'],
        ['publish', '--repository', 'DataDog/marketplace', '--commit', 'a' * 40, '--dry-run'],
        ['tag', '--repository', 'DataDog/marketplace', '--commit', 'a' * 40, '--retention-days', '3'],
        ['cleanup', '--repository', 'DataDog/marketplace', '--commit', 'a' * 40, '--retention-days', '0'],
        ['release', '--repository', 'DataDog/marketplace', '--commit', 'a' * 40],
    ],
)
def test_rejects_options_for_other_actions(args: list[str]):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2


def test_rejects_abbreviated_options(capsys: pytest.CaptureFixture[str]):
    with patch.object(Release, 'needs_package', return_value=False), pytest.raises(SystemExit) as error:
        main(['check', '--repository', 'DataDog/marketplace', '--commit', 'a' * 40, '--dir', 'dist'])
    assert error.value.code == 2
    assert 'unrecognized arguments: --dir dist' in capsys.readouterr().err


def test_invalid_identity_fails_without_traceback(capsys: pytest.CaptureFixture[str]):
    assert main(['check', '--repository', 'DataDog/marketplace', '--commit', 'A' * 40]) == 1
    assert capsys.readouterr().err == 'Error: commit must be a full, lowercase Git SHA\n'
