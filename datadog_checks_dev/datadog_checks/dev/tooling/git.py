# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

from ..subprocess import run_command
from ..utils import chdir
from .constants import get_root


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


def get_commits_since(check_name, target_tag=None):
    """
    Get the list of commits from `target_tag` to `HEAD` for the given check
    """
    root = get_root()
    target_path = os.path.join(root, check_name)
    command = 'git log --pretty=%s {}{}'.format('' if target_tag is None else '{}... '.format(target_tag), target_path)

    with chdir(root):
        return run_command(command, capture=True).stdout.splitlines()


def git_show_file(path, ref):
    """
    Return the contents of a file at a given tag
    """
    root = get_root()
    command = 'git show {}:{}'.format(ref, path)

    with chdir(root):
        return run_command(command, capture=True).stdout


def git_commit(targets, message, force=False, sign=False):
    """
    Commit the changes for the given targets.
    """
    root = get_root()
    target_paths = []
    for t in targets:
        target_paths.append(os.path.join(root, t))

    with chdir(root):
        result = run_command('git add{} {}'.format(' -f' if force else '', ' '.join(target_paths)))
        if result.code != 0:
            return result

        return run_command('git commit{} -m "{}"'.format(' -S' if sign else '', message))


def git_tag(tag_name, push=False):
    """
    Tag the repo using an annotated tag.
    """
    with chdir(get_root()):
        result = run_command('git tag -a {} -m "{}"'.format(tag_name, tag_name), capture=True)

        if push:
            if result.code != 0:
                return result
            return run_command('git push origin {}'.format(tag_name), capture=True)

        return result


def git_tag_list(pattern=None):
    """
    Return a list of all the tags in the git repo matching a regex passed in
    `pattern`. If `pattern` is None, return all the tags.
    """
    with chdir(get_root()):
        result = run_command('git tag', capture=True).stdout
        result = result.splitlines()

    if not pattern:
        return result

    regex = re.compile(pattern)
    return list(filter(regex.search, result))


def tracked_by_git(filename):
    """
    Return a boolean value for whether the given file is tracked by git.
    """
    with chdir(get_root()):
        # https://stackoverflow.com/a/2406813
        result = run_command('git ls-files --error-unmatch {}'.format(filename), capture=True)
        return result.code == 0


def ignored_by_git(filename):
    """
    Return a boolean value for whether the given file is ignored by git.
    """
    with chdir(get_root()):
        result = run_command('git check-ignore -q {}'.format(filename), capture=True)
        return result.code == 0
