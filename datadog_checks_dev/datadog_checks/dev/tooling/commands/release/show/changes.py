# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from ....constants import get_root
from ....utils import complete_valid_checks, get_valid_checks, get_version_string
from ...console import (
    CONTEXT_SETTINGS,
    abort,
    echo_info,
    validate_check_arg,
)


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Show all the pending PRs for a given check.')
@click.argument('check', shell_complete=complete_valid_checks, callback=validate_check_arg)
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
def changes(check, tag_pattern, tag_prefix, dry_run, since):
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

    applicable_changelog_types = set()
    fragment_dir = os.path.join(get_root(), check, 'changelog.d')
    if not os.path.exists(fragment_dir):
        echo_info('No changes for this check.')
        return cur_version, applicable_changelog_types
    changes_to_report = []
    for fname in os.listdir(fragment_dir):
        applicable_changelog_types.add(fname.split(".")[1])
        changes_to_report.append(f'{os.path.join(check, "changelog.d", fname)}:')
        fpath = os.path.join(fragment_dir, fname)
        with open(fpath, mode='r') as fh:
            changes_to_report.append(fh.read() + '\n')
    echo_info('\n'.join(changes_to_report).rstrip())

    return cur_version, applicable_changelog_types
