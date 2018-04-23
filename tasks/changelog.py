# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals
import os
import re
import sys
import json
import urllib2
import StringIO
from collections import namedtuple
from datetime import datetime

from invoke import task
from invoke.exceptions import Exit

from .constants import ROOT, GITHUB_API_URL


# match something like `(#1234)` and return `1234` in a group
PR_REG = re.compile(r'\(\#(\d+)\)')

ChangelogEntry = namedtuple('ChangelogEntry', 'number, title, url')


def get_version_string(check_name):
    """
    Get the version string for the given check.
    """
    about = {}
    about_path = os.path.join(ROOT, check_name, "datadog_checks", check_name, "__about__.py")
    with open(about_path) as f:
        exec(f.read(), about)

    return about.get('__version__')


def get_release_tag_string(check_name, version_string):
    """
    Compose a string to use for release tags
    """
    return '{}-{}'.format(check_name, version_string)


def parse_pr_numbers(git_log_lines):
    """
    Parse PR numbers from commit messages. At GitHub those have the format:

        `here is the message (#1234)`

    being `1234` the PR number.
    """
    prs = []
    for line in git_log_lines:
        match = re.search(PR_REG, line)
        if match:
            prs.append(match.group(1))
    return prs


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
    # get the current version
    version_string = get_version_string(target)
    if not version_string:
        raise Exit("Unable to get version for check {}".format(target))
    print("Current version of check {}: {}".format(target, version_string))

    # get the name of the current release tag
    target_tag = get_release_tag_string(target, version_string)

    # get the diff from HEAD
    target_path = os.path.join(ROOT, target)
    cmd = 'git log --pretty=%s {}... {}'.format(target_tag, target_path)
    diff_lines = ctx.run(cmd, hide='out').stdout.split('\n')

    # for each PR get the title, we'll use it to populate the changelog
    endpoint = GITHUB_API_URL + '/repos/DataDog/integrations-core/pulls/{}'
    pr_numbers = parse_pr_numbers(diff_lines)
    print("Found {} PRs merged since tag: {}".format(len(pr_numbers), target_tag))

    entries = []
    for pr_num in pr_numbers:
        try:
            response = urllib2.urlopen(endpoint.format(pr_num))
        except Exception as e:
            sys.stderr.write("Unable to fetch info for PR #{}\n: {}".format(pr_num, e))
            continue

        payload = json.loads(response.read())
        entry = ChangelogEntry(pr_num, payload.get('title'), payload.get('html_url'))
        entries.append(entry)

    # store the new changelog in memory
    output = StringIO.StringIO()

    # the header contains version and date
    header = "### {} / {}\n".format(new_version, datetime.now().strftime("%Y-%m-%d"))
    output.write(header)

    # one bullet point for each PR
    output.write("\n")
    for entry in entries:
        output.write("* {}. See [#{}]({}).\n".format(entry.title, entry.number, entry.url))
    output.write("\n")

    # read the old contents
    changelog_path = os.path.join(ROOT, target, "CHANGELOG.md")
    with open(changelog_path, 'r') as f:
        old = f.readlines()

    # write the new changelog in memory
    changelog = StringIO.StringIO()

    # preserve the title
    changelog.write("".join(old[:2]))

    # prepend the new changelog to the old contents
    # make the command idempotent
    if header not in old:
        changelog.write(output.getvalue())

    # append the rest of the old changelog
    changelog.write("".join(old[2:]))

    # print on the standard out in case of a dry run
    if dry_run:
        print(changelog.getvalue())
        sys.exit(0)

    # overwrite the old changelog
    with open(changelog_path, 'w') as f:
        f.write(changelog.getvalue())
