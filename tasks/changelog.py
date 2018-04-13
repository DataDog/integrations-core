# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals
import os
import re

from invoke import task
from invoke.exceptions import Exit

from .constants import ROOT


# match something like `(#1234)` and return `1234` in a group
PR_REG = re.compile(r'\(\#(\d+)\)')


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
def make_changelog(ctx, target, dry_run=False):
    """
    Write the changelog for the given check

    Example invocation:
        inv make-changelog redisdb
    """
    # get the current version
    version_string = get_version_string(target)
    if not version_string:
        raise Exit("Unable to get version for check {}".format(target))

    # get the name of the current release tag
    target_tag = get_release_tag_string(target, version_string)

    print(target, target_tag)

    # get the diff from HEAD
    target_path = os.path.join(ROOT, target)
    cmd = 'git log --pretty=%s 6.1.1... {}'.format(target_path)
    diff_lines = ctx.run(cmd, hide='out').stdout.split('\n')

    # get the PR numbers
    print(parse_pr_numbers(diff_lines))





