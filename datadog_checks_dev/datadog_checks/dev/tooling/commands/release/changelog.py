# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import namedtuple

import click
from semver import VersionInfo

from ...utils import complete_testable_checks, get_valid_checks, get_version_string
from ..console import CONTEXT_SETTINGS, abort, echo_info, run_or_abort, validate_check_arg

ChangelogEntry = namedtuple('ChangelogEntry', 'number, title, url, author, author_url, from_contributor')


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Update the changelog for a check')
@click.argument('check', shell_complete=complete_testable_checks, callback=validate_check_arg)
@click.argument('version')
@click.argument('old_version', required=False)
@click.option('--end')
@click.option('--initial', is_flag=True)
@click.option('--organization', '-r', default='DataDog')
@click.option('--quiet', '-q', is_flag=True)
@click.option('--dry-run', '-n', is_flag=True)
@click.option('--output-file', '-o', default='CHANGELOG.md', show_default=True)
@click.option('--tag-pattern', default=None, hidden=True)
@click.option('--tag-prefix', '-tp', default='v', show_default=True)
@click.option('--no-semver', '-ns', default=False, is_flag=True)
@click.option('--exclude-branch', default=None, help="Exclude changes comming from a specific branch")
@click.pass_context
def changelog(
    ctx,
    check,
    version,
    old_version,
    end,
    initial,
    quiet,
    dry_run,
    output_file,
    tag_pattern,
    tag_prefix,
    no_semver,
    organization,
    exclude_branch,
):
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

    run_or_abort(["towncrier", "build", "--dir", check, "--config", "towncrier.toml", "--version", version])
