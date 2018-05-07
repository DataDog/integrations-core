# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals
import os

from packaging import version
from invoke import task, call
from invoke.exceptions import Exit

from .constants import AGENT_BASED_INTEGRATIONS, ROOT
from .utils import get_version_string, get_current_branch, get_release_tag_string
from .changelog import do_update_changelog


def update_version_module(check_name, old_ver, new_ver):
    """
    Change the Python code in the __about__.py module so that `__version__`
    contains the new value.
    """
    about_module = os.path.join(check_name, 'datadog_checks', check_name, '__about__.py')
    with open(about_module, 'r') as f:
        contents = f.read()

    contents = contents.replace(old_ver, new_ver)
    with open(about_module, 'w') as f:
        f.write(contents)


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
    cmd = 'git tag {} -m"{}"'.format(tag_name, tag_name)
    ctx.run(cmd)


@task(help={
        'target': "The check to release",
        'new_version': "The new version",
        'dry-run': "Runs the task without actually doing anything",
})
def release_check(ctx, target, new_version, dry_run=False):
    """
    Perform a set of operations needed to release a single check:

     * update the version in __about__.py
     * update the changelog
     * commit the above changes
     * tag the repo with a tag in the form `check-name_0_0_1`

    Example invocation:
        inv release-check redisdb 3.1.1
    """
    # sanity check on the target
    if target not in AGENT_BASED_INTEGRATIONS:
        raise Exit("Provided target is not an Agent-based Integration")

    # don't run the task on the master branch
    if get_current_branch(ctx) == 'master':
        raise Exit("This task will add a commit, you don't want to add it on master directly")

    # sanity check on the version provided
    p_version = version.parse(new_version)
    p_current = version.parse(get_version_string(target))
    if p_version <= p_current:
        raise Exit("Current version is {}, can't bump to {}".format(p_current, p_version))

    # update the version number
    print("Current version of check {}: {}, bumping to: {}".format(target, p_current, p_version))
    cur_version = get_version_string(target)
    update_version_module(target, cur_version, new_version)

    # update the CHANGELOG
    print("Updating the changelog")
    do_update_changelog(ctx, target, cur_version, new_version)

    # commit the changes
    msg = "Bumped to {}".format(new_version)
    git_commit(ctx, target, msg)

    # tagging
    tag = get_release_tag_string(target, new_version)
    print("Tagging repo with tag: {}".format(tag))
    git_tag(ctx, tag)

    # done
    print("All done, remember to open a PR to merge these changes on master")
