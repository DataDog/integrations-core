# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals
import os
import sys
from collections import namedtuple
from datetime import datetime

from six import StringIO
from invoke import task
from invoke.exceptions import Exit
from semver import parse_version_info

from .constants import ROOT, AGENT_BASED_INTEGRATIONS
from .utils.common import get_version_string, get_release_tag_string
from .utils.git import parse_pr_numbers, get_diff
from .utils.github import get_changelog_types, from_contributor, get_pr

CHANGELOG_LABEL_PREFIX = 'changelog/'
CHANGELOG_TYPE_NONE = 'no-changelog'
CHANGELOG_TYPES = [
    'Added',
    'Changed',
    'Deprecated',
    'Fixed',
    'Removed',
    'Security',
]

ChangelogEntry = namedtuple('ChangelogEntry', 'number, title, url, author, author_url, from_contributor')


@task(help={
    'target': "The check to compile the changelog for",
    'dry-run': "Runs the task without actually doing anything",
})
def update_changelog(ctx, target, new_version, dry_run=False):
    """
    Update the changelog for the given check with the changes
    since the current release.

    Example invocation:
        inv update-changelog redisdb 3.1.1
    """
    # sanity check on the target
    if target not in AGENT_BASED_INTEGRATIONS:
        raise Exit("Provided target is not an Agent-based Integration")

    # sanity check on the version provided
    cur_version = get_version_string(target)
    if parse_version_info(new_version) <= parse_version_info(cur_version):
        raise Exit("Current version is {}, can't bump to {}".format(cur_version, new_version))

    print("Current version of check {}: {}, bumping to: {}".format(target, cur_version, new_version))
    do_update_changelog(ctx, target, cur_version, new_version, dry_run)


def do_update_changelog(ctx, target, cur_version, new_version, dry_run=False):
    """
    Actually perform the operations needed to update the changelog, this
    method is supposed to be used by other tasks and not directly.
    """
    # get the name of the current release tag
    target_tag = get_release_tag_string(target, cur_version)

    # get the diff from HEAD
    diff_lines = get_diff(ctx, target, target_tag)

    # for each PR get the title, we'll use it to populate the changelog
    pr_numbers = parse_pr_numbers(diff_lines)
    print("Found {} PRs merged since tag: {}".format(len(pr_numbers), target_tag))
    entries = []
    for pr_num in pr_numbers:
        try:
            payload = get_pr(pr_num)
        except Exception as e:
            sys.stderr.write("Unable to fetch info for PR #{}\n: {}".format(pr_num, e))
            continue

        changelog_labels = get_changelog_types(payload)

        if not changelog_labels:
            raise Exit("No valid changelog labels found attached to PR #{}, please add one".format(pr_num))
        elif len(changelog_labels) > 1:
            raise Exit("Multiple changelog labels found attached to PR #{}, please use only one".format(pr_num))

        changelog_type = changelog_labels[0]
        if changelog_type == CHANGELOG_TYPE_NONE:
            # No changelog entry for this PR
            print("Skipping PR #{} from changelog".format(pr_num))
            continue

        author = payload.get('user', {}).get('login')
        author_url = payload.get('user', {}).get('html_url')
        title = '[{}] {}'.format(changelog_type, payload.get('title'))

        entry = ChangelogEntry(pr_num, title, payload.get('html_url'),
                               author, author_url, from_contributor(payload))

        entries.append(entry)

    # store the new changelog in memory
    new_entry = StringIO()

    # the header contains version and date
    header = "## {} / {}\n".format(new_version, datetime.now().strftime("%Y-%m-%d"))
    new_entry.write(header)

    # one bullet point for each PR
    new_entry.write("\n")
    for entry in entries:
        thanknote = ""
        if entry.from_contributor:
            thanknote = " Thanks [{}]({}).".format(entry.author, entry.author_url)
        new_entry.write("* {}. See [#{}]({}).{}\n".format(entry.title, entry.number, entry.url, thanknote))
    new_entry.write("\n")

    # read the old contents
    changelog_path = os.path.join(ROOT, target, "CHANGELOG.md")
    with open(changelog_path, 'r') as f:
        old = f.readlines()

    # write the new changelog in memory
    changelog = StringIO()

    # preserve the title
    changelog.write("".join(old[:2]))

    # prepend the new changelog to the old contents
    # make the command idempotent
    if header not in old:
        changelog.write(new_entry.getvalue())

    # append the rest of the old changelog
    changelog.write("".join(old[2:]))

    # print on the standard out in case of a dry run
    if dry_run:
        print(changelog.getvalue())
        sys.exit(0)

    # overwrite the old changelog
    with open(changelog_path, 'w') as f:
        f.write(changelog.getvalue())
