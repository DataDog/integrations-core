# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import subprocess
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from datadog_checks.dev.tooling.commands.release.tag import tag
from datadog_checks.dev.tooling.constants import set_root

REPO_ROOT = str(Path(__file__).parents[5])
set_root(REPO_ROOT)


def test_new_version_appears_in_output():
    # Bump two checks to a version that has no git tag
    activemq_about = Path(f'{REPO_ROOT}/activemq/datadog_checks/activemq/__about__.py')
    btrfs_about = Path(f'{REPO_ROOT}/btrfs/datadog_checks/btrfs/__about__.py')
    original_activemq = activemq_about.read_text()
    original_btrfs = btrfs_about.read_text()
    activemq_about.write_text(re.sub(r"(?<=__version__ = ')[^']+", '99.99.99', original_activemq))
    btrfs_about.write_text(re.sub(r"(?<=__version__ = ')[^']+", '99.99.99', original_btrfs))
    try:
        runner = CliRunner()
        result = runner.invoke(tag, ['--no-fetch', '--no-push', '--dry-run', 'all'], catch_exceptions=False)
    finally:
        activemq_about.write_text(original_activemq)
        btrfs_about.write_text(original_btrfs)

    assert result.exit_code == 0
    assert 'activemq-99.99.99' in result.output
    assert 'btrfs-99.99.99' in result.output
    assert 'Tagged 2 release(s)' in result.output


def test_existing_tag_silent_by_default():
    activemq_about = Path(f'{REPO_ROOT}/activemq/datadog_checks/activemq/__about__.py')
    original = activemq_about.read_text()
    activemq_about.write_text(re.sub(r"(?<=__version__ = ')[^']+", '99.99.99', original))
    subprocess.run(
        ['git', '-C', REPO_ROOT, '-c', 'tag.gpgsign=false', 'tag', 'activemq-99.99.99'], check=True, capture_output=True
    )
    try:
        result = CliRunner().invoke(tag, ['--no-fetch', '--no-push', '--dry-run', 'activemq'], catch_exceptions=False)
    finally:
        activemq_about.write_text(original)
        subprocess.run(['git', '-C', REPO_ROOT, 'tag', '-d', 'activemq-99.99.99'], check=True, capture_output=True)

    assert result.exit_code == 2
    assert 'Tagged 0 release(s), skipped 1 already-tagged release(s).' in result.output


def test_existing_tag_debug_message():
    activemq_about = Path(f'{REPO_ROOT}/activemq/datadog_checks/activemq/__about__.py')
    original = activemq_about.read_text()
    activemq_about.write_text(re.sub(r"(?<=__version__ = ')[^']+", '99.99.99', original))
    subprocess.run(
        ['git', '-C', REPO_ROOT, '-c', 'tag.gpgsign=false', 'tag', 'activemq-99.99.99'], check=True, capture_output=True
    )
    try:
        with patch('datadog_checks.dev.tooling.commands.console.DEBUG_OUTPUT', True):
            result = CliRunner().invoke(
                tag, ['--no-fetch', '--no-push', '--dry-run', 'activemq'], catch_exceptions=False
            )
    finally:
        activemq_about.write_text(original)
        subprocess.run(['git', '-C', REPO_ROOT, 'tag', '-d', 'activemq-99.99.99'], check=True, capture_output=True)

    assert result.exit_code == 2
    assert 'activemq-99.99.99 already exists' in result.output
    assert 'Tagged 0 release(s), skipped 1 already-tagged release(s).' in result.output
