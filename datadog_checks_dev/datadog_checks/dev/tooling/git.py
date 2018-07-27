# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from .constants import get_root
from .utils import parse_pr_number
from ..subprocess import run_command
from ..utils import chdir


def get_current_branch():
    """
    Get the current branch name.
    """
    command = 'git rev-parse --abbrev-ref HEAD'

    with chdir(get_root()):
        return run_command(command, capture='out').stdout.strip()


def files_changed():
    """
    Return the list of file changed in the current branch compared to `master`
    """
    with chdir(get_root()):
        result = run_command('git diff --name-only master...', capture='out')
    changed_files = result.stdout.splitlines()

    # Remove empty lines
    return [f for f in changed_files if f]


def parse_pr_numbers(git_log_lines):
    """
    Parse PR numbers from commit messages. At GitHub those have the format:

        `here is the message (#1234)`

    being `1234` the PR number.
    """
    prs = []
    for line in git_log_lines:
        pr_number = parse_pr_number(line)
        if pr_number:
            prs.append(pr_number)
    return prs


def get_diff(check_name, target_tag):
    """
    Get the git diff from HEAD for the given check
    """
    root = get_root()
    target_path = os.path.join(root, check_name)
    command = 'git log --pretty=%s {}... {}'.format(target_tag, target_path)

    with chdir(root):
        return run_command(command, capture='out').stdout.splitlines()


def git_commit(targets, message):
    """
    Commit the changes for the given targets.
    """
    root = get_root()
    target_paths = []
    for t in targets:
        target_paths.append(os.path.join(root, t))

    with chdir(root):
        result = run_command('git add {}'.format(' '.join(target_paths)))
        if result.code != 0:
            return result

        return run_command('git commit -m "{}"'.format(message))


def git_tag(tag_name, push=False):
    """
    Tag the repo using an annotated tag.
    """
    with chdir(get_root()):
        result = run_command('git tag -a {} -m "{}"'.format(tag_name, tag_name))

        if push:
            if result.code != 0:
                return result
            return run_command('git push origin {}'.format(tag_name))

        return result
