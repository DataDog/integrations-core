# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals
import re
import os

from ..constants import ROOT

# match something like `(#1234)` and return `1234` in a group
PR_REG = re.compile(r'\(\#(\d+)\)')


def get_current_branch(ctx):
    """
    Get the current branch name.
    """
    cmd = "git rev-parse --abbrev-ref HEAD"
    return ctx.run(cmd, hide='out').stdout


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


def get_diff(ctx, check_name, target_tag):
    """
    Get the git diff from HEAD for the given check
    """
    target_path = os.path.join(ROOT, check_name)
    cmd = 'git log --pretty=%s {}... {}'.format(target_tag, target_path)
    return ctx.run(cmd, hide='out').stdout.split('\n')


def git_commit(ctx, target, message):
    """
    Commit the current changes.
    """
    target_path = os.path.join(ROOT, target)
    cmd = 'git add ' + target_path
    ctx.run(cmd)
    cmd = 'git commit -m"{}"'.format(message)
    ctx.run(cmd)


def git_tag(ctx, tag_name):
    """
    Tag the repo using an annotated tag.
    """
    cmd = 'git tag -a {} -m"{}"'.format(tag_name, tag_name)
    ctx.run(cmd)
