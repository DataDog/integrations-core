# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections import defaultdict, namedtuple
from datetime import datetime
from io import StringIO

import click
from semver import parse_version_info

from ....fs import stream_file_lines, write_file
from ...constants import CHANGELOG_TYPE_NONE, CHANGELOG_TYPES_ORDERED, get_root
from ...git import get_commits_since
from ...github import from_contributor, get_changelog_types, get_pr, parse_pr_numbers
from ...release import get_release_tag_string
from ...utils import complete_testable_checks, get_valid_checks, get_version_string
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, validate_check_arg

ChangelogEntry = namedtuple('ChangelogEntry', 'number, title, url, author, author_url, from_contributor')


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Update the changelog for a check')
@click.argument('check', autocompletion=complete_testable_checks, callback=validate_check_arg)
@click.argument('version')
@click.argument('old_version', required=False)
@click.option('--initial', is_flag=True)
@click.option('--organization', '-r', default='DataDog')
@click.option('--quiet', '-q', is_flag=True)
@click.option('--dry-run', '-n', is_flag=True)
@click.option('--output-file', '-o', default='CHANGELOG.md', show_default=True)
@click.option('--tag-prefix', '-tp', default='v', show_default=True)
@click.option('--no-semver', '-ns', default=False, is_flag=True)
@click.pass_context
def changelog(
    ctx, check, version, old_version, initial, quiet, dry_run, output_file, tag_prefix, no_semver, organization
):
    """Perform the operations needed to update the changelog.

    This method is supposed to be used by other tasks and not directly.
    """
    if check and check not in get_valid_checks():
        abort(f'Check `{check}` is not an Agent-based Integration')

    # sanity check on the version provided
    cur_version = old_version or get_version_string(check, tag_prefix=tag_prefix)
    if not cur_version:
        abort(
            'Failed to retrieve the latest version. Please ensure your project or check has a proper set of tags '
            'following SemVer and matches the provided tag_prefix and/or tag_pattern.'
        )

    if not no_semver and parse_version_info(version.replace(tag_prefix, '', 1)) <= parse_version_info(
        cur_version.replace(tag_prefix, '', 1)
    ):
        abort(f'Current version is {cur_version}, cannot bump to {version}')

    if not quiet:
        echo_info(f'Current version of check {check}: {cur_version}, bumping to: {version}')

    # get the name of the current release tag
    target_tag = get_release_tag_string(check, cur_version)

    # get the diff from HEAD
    diff_lines = get_commits_since(check, None if initial else target_tag)

    # for each PR get the title, we'll use it to populate the changelog
    pr_numbers = parse_pr_numbers(diff_lines)
    if not quiet:
        echo_info(f'Found {len(pr_numbers)} PRs merged since tag: {target_tag}')

    if initial:
        # Only use the first one
        del pr_numbers[:-1]

    user_config = ctx.obj
    entries = defaultdict(list)
    generated_changelogs = 0
    for pr_num in pr_numbers:
        try:
            payload = get_pr(pr_num, user_config, org=organization)
        except Exception as e:
            echo_failure(f'Unable to fetch info for PR #{pr_num}: {e}')
            continue

        changelog_labels = get_changelog_types(payload)

        if not changelog_labels:
            abort(f'No valid changelog labels found attached to PR #{pr_num}, please add one!')
        elif len(changelog_labels) > 1:
            abort(f'Multiple changelog labels found attached to PR #{pr_num}, please only use one!')

        changelog_type = changelog_labels[0]
        if changelog_type == CHANGELOG_TYPE_NONE:
            if not quiet:
                # No changelog entry for this PR
                echo_info(f'Skipping PR #{pr_num} from changelog due to label')
            continue

        generated_changelogs += 1

        author = payload.get('user', {}).get('login')
        author_url = payload.get('user', {}).get('html_url')
        title = f"[{changelog_type}] {payload.get('title')}"

        entry = ChangelogEntry(pr_num, title, payload.get('html_url'), author, author_url, from_contributor(payload))

        entries[changelog_type].append(entry)

    # store the new changelog in memory
    new_entry = StringIO()

    # the header contains version and date
    header = f"## {version} / {datetime.utcnow().strftime('%Y-%m-%d')}\n"
    new_entry.write(header)

    # one bullet point for each PR
    new_entry.write('\n')
    for changelog_type in CHANGELOG_TYPES_ORDERED:
        for entry in entries[changelog_type]:
            thanks_note = ''
            if entry.from_contributor:
                thanks_note = f' Thanks [{entry.author}]({entry.author_url}).'
            new_entry.write(f'* {entry.title}. See [#{entry.number}]({entry.url}).{thanks_note}\n')
    new_entry.write('\n')

    # read the old contents
    if check:
        changelog_path = os.path.join(get_root(), check, output_file)
    else:
        changelog_path = os.path.join(get_root(), output_file)
    old = list(stream_file_lines(changelog_path))

    # write the new changelog in memory
    changelog_buffer = StringIO()

    # preserve the title
    changelog_buffer.write(''.join(old[:2]))

    # prepend the new changelog to the old contents
    # make the command idempotent
    if header not in old:
        changelog_buffer.write(new_entry.getvalue())

    # append the rest of the old changelog
    changelog_buffer.write(''.join(old[2:]))

    # print on the standard out in case of a dry run
    if dry_run:
        echo_info(changelog_buffer.getvalue())
    else:
        # overwrite the old changelog
        write_file(changelog_path, changelog_buffer.getvalue())
        echo_success(f"Successfully generated {generated_changelogs} change{'s' if generated_changelogs > 1 else ''}")
