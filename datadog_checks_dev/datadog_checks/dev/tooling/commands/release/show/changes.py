# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from .....fs import stream_file_lines
from ....constants import get_root
from ....utils import complete_valid_checks, get_valid_checks, get_version_string
from ...console import (
    CONTEXT_SETTINGS,
    abort,
    validate_check_arg,
)


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Show all the pending PRs for a given check.')
@click.argument('check', shell_complete=complete_valid_checks, callback=validate_check_arg)
@click.option('--organization', '-r', default='DataDog', help="The Github organization the repository belongs to")
@click.option(
    '--tag-pattern',
    default=None,
    help="The regex pattern for the format of the tag. Required if the tag doesn't follow semver",
)
@click.option(
    '--tag-prefix', default=None, help="Specify the prefix of the tag to use if the tag doesn't follow semver"
)
@click.option('--dry-run', '-n', is_flag=True, help="Run the command in dry-run mode")
@click.option(
    '--since', default=None, help="The git ref to use instead of auto-detecting the tag to view changes since"
)
@click.option('--end')
@click.option('--exclude-branch', default=None, help="Exclude changes comming from a specific branch")
@click.pass_context
def changes(ctx, check, tag_pattern, tag_prefix, dry_run, organization, since, end, exclude_branch):
    """Show all the pending PRs for a given check."""
    if not dry_run and check and check not in get_valid_checks():
        abort(f'Check `{check}` is not an Agent-based Integration')

    # get the name of the current release tag
    cur_version = since or get_version_string(check, pattern=tag_pattern, tag_prefix=tag_prefix)
    if not cur_version:
        abort(
            'Failed to retrieve the latest version. Please ensure your project or check has a proper set of tags '
            'following SemVer and matches the provided tag_prefix and/or tag_pattern.'
        )

    if check:
        changelog_path = os.path.join(get_root(), check, 'CHANGELOG.md')
    else:
        changelog_path = os.path.join(get_root(), 'CHANGELOG.md')
    log = list(stream_file_lines(changelog_path))

    header_index = 2
    for index in range(2, len(log)):
        if log[index].startswith("##") and "## Unreleased" not in log[index]:
            header_index = index
            break

    if header_index == 4:
        abort('There are no changes for this integration')

    unreleased = log[4:header_index]
    applicable_changelog_types = []

    for line in unreleased:
        if line.startswith('***'):
            applicable_changelog_types.append(line[3:-5])

    return cur_version, applicable_changelog_types
