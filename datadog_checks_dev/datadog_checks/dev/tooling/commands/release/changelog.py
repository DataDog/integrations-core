# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections import namedtuple
from datetime import date, datetime
from io import StringIO

import click
from semver import VersionInfo

from ....fs import stream_file_lines, write_file
from ...constants import get_root
from ...utils import complete_testable_checks, get_valid_checks, get_version_string
from ..console import CONTEXT_SETTINGS, abort, echo_info, echo_success, validate_check_arg

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

    # read the old contents
    if check:
        changelog_path = os.path.join(get_root(), check, output_file)
    else:
        changelog_path = os.path.join(get_root(), output_file)
    old = list(stream_file_lines(changelog_path))

    if initial:
        # For initial releases, just keep the ddev generated CHANGELOG but update the date to today
        for idx, line in enumerate(old):
            if line.startswith("## 1.0.0"):
                old[idx] = f"## 1.0.0 / {date.today()}\n"
                break
        write_result(dry_run, changelog_path, ''.join(old), num_changes=1)
        return

    # find the first header below the Unreleased section
    header_index = 2
    for index in range(2, len(old)):
        if old[index].startswith("##") and "## Unreleased" not in old[index]:
            header_index = index
            break

    # get text from the unreleased section
    if header_index == 4:
        abort('There are no changes for this integration')

    changelogs = old[4:header_index]
    num_changelogs = 0
    for line in changelogs:
        if line.startswith('* '):
            num_changelogs += 1

    # the header contains version and date
    header = f"## {version} / {datetime.utcnow().strftime('%Y-%m-%d')}\n"

    # store the new changelog in memory
    new_entry = StringIO()
    new_entry.write(header)
    new_entry.write('\n')

    # write the new changelog in memory
    changelog_buffer = StringIO()

    # preserve the title and unreleased section
    changelog_buffer.write(''.join(old[:4]))

    # prepend the new changelog to the old contents
    # make the command idempotent
    if header not in old:
        changelog_buffer.write(new_entry.getvalue())

    # append the rest of the old changelog
    changelog_buffer.write(''.join(old[4:]))

    write_result(dry_run, changelog_path, changelog_buffer.getvalue(), num_changelogs)


def write_result(dry_run, changelog_path, final_output, num_changes):
    # print on the standard out in case of a dry run
    if dry_run:
        echo_info(final_output)
    else:
        # overwrite the old changelog
        write_file(changelog_path, final_output)
        echo_success(f"Successfully generated {num_changes} change{'s' if num_changes > 1 else ''}")
