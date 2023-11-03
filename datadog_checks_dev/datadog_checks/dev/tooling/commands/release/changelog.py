# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys
from collections import namedtuple

import click
from semver import VersionInfo

from datadog_checks.dev.tooling.constants import get_root

from ...utils import complete_testable_checks, get_valid_checks, get_version_string
from ..console import CONTEXT_SETTINGS, abort, echo_info, run_or_abort, validate_check_arg

ChangelogEntry = namedtuple('ChangelogEntry', 'number, title, url, author, author_url, from_contributor')


def towncrier(target_dir, cmd, *cmd_args):
    '''
    Run towncrier command with its arguments in target_dir.
    '''
    tc_res = run_or_abort(
        [
            sys.executable,
            "-m",
            "towncrier",
            cmd,
            "--config",
            os.path.join(get_root(), "towncrier.toml"),
            "--dir",
            target_dir,
            *cmd_args,
        ],
        capture='both',
    )
    echo_info(tc_res.stdout.rstrip())
    return tc_res


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Update the changelog for a check')
@click.argument('check', shell_complete=complete_testable_checks, callback=validate_check_arg)
@click.argument('version')
@click.argument('old_version', required=False)
@click.option('--quiet', '-q', is_flag=True)
@click.option('--dry-run', '-n', is_flag=True)
@click.option('--tag-pattern', default=None, hidden=True)
@click.option('--tag-prefix', '-tp', default='v', show_default=True)
@click.option('--no-semver', '-ns', default=False, is_flag=True)
@click.option('--date', default=None)
def changelog(check, version, old_version, quiet, dry_run, tag_pattern, tag_prefix, no_semver, date):
    """Perform the operations needed to update the changelog.

    This method is supposed to be used by other tasks and not directly.
    """
    if check and check not in get_valid_checks():
        abort(f'Check `{check}` is not an Agent-based Integration')

    # sanity check on the version provided
    cur_version = old_version or get_version_string(check, pattern=tag_pattern, tag_prefix=tag_prefix)
    if not cur_version:
        abort(
            'Failed to retrieve the latest version. Please ensure your project or check has a proper set of tags '
            'following SemVer and matches the provided tag_prefix and/or tag_pattern.'
        )

    if not no_semver and VersionInfo.parse(version.replace(tag_prefix, '', 1)) <= VersionInfo.parse(
        cur_version.replace(tag_prefix, '', 1)
    ):
        abort(f'Current version is {cur_version}, cannot bump to {version}')

    if not quiet:
        echo_info(f'Current version of check {check}: {cur_version}, bumping to: {version}')

    build_args = ["--yes", "--version", version]
    if dry_run:
        build_args.append("--draft")
    if date:
        build_args.extend(["--date", date])
    towncrier(os.path.join(get_root(), check), "build", *build_args)
