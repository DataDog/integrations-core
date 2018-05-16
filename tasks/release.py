# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals
import os

from packaging import version
from invoke import task
from invoke.exceptions import Exit

from .constants import (
    AGENT_BASED_INTEGRATIONS, ROOT, AGENT_REQ_FILE, AGENT_V5_ONLY
)
from .utils import (
    get_version_string, get_current_branch, get_release_tag_string,
    load_manifest
)
from .changelog import do_update_changelog


def update_version_module(check_name, old_ver, new_ver):
    """
    Change the Python code in the __about__.py module so that `__version__`
    contains the new value.
    """
    about_module = os.path.join(ROOT, check_name, 'datadog_checks', check_name, '__about__.py')
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
    cmd = 'git tag -a {} -m"{}"'.format(tag_name, tag_name)
    ctx.run(cmd)


@task(help={
    'target': "The check to tag",
    'dry-run': "Runs the task without actually doing anything",
})
def tag_current_release(ctx, target, version=None, dry_run=False):
    """
    Tag the HEAD of the git repo with the current release number for a
    specific check. This is a maintainance task that should be run under
    very specific circumstances (e.g. for whatever reason the release process
    for a check is being done manually).
    """
    # get the current version
    if version is None:
        version = get_version_string(target)

    # get the tag name
    tag = get_release_tag_string(target, version)
    print("Tagging HEAD with {}".format(tag))
    if dry_run:
        return

    try:
        git_tag(ctx, tag)
    except Exception as e:
        print(e)


@task(help={
    'target': "The check to release",
    'new_version': "The new version",
})
def release_prepare(ctx, target, new_version):
    """
    Perform a set of operations needed to release a single check:

     * update the version in __about__.py
     * update the changelog
     * commit the above changes
     * tag the repo with a tag in the form `check-name_0_0_1`

    Example invocation:
        inv release-prepare redisdb 3.1.1
    """
    # sanity check on the target
    if target not in AGENT_BASED_INTEGRATIONS:
        raise Exit("Provided target is not an Agent-based Integration")

    # don't run the task on the master branch
    if get_current_branch(ctx) == 'master':
        raise Exit("This task will add a commit, you don't want to add it on master directly")

    # sanity check on the version provided
    cur_version = get_version_string(target)
    p_version = version.parse(new_version)
    p_current = version.parse(cur_version)
    if p_version <= p_current:
        raise Exit("Current version is {}, can't bump to {}".format(p_current, p_version))

    # update the version number
    print("Current version of check {}: {}, bumping to: {}".format(target, p_current, p_version))
    update_version_module(target, cur_version, new_version)

    # update the CHANGELOG
    print("Updating the changelog")
    do_update_changelog(ctx, target, cur_version, new_version)

    # commit the changes
    msg = "Bumped version to {}".format(new_version)
    git_commit(ctx, target, msg)

    # tagging
    tag = get_release_tag_string(target, new_version)
    print("Tagging repo with tag: {}".format(tag))
    git_tag(ctx, tag)

    # done
    print("All done, remember to open a PR to merge these changes on master")


@task(help={
    'target': "The check to release",
    'dry-run': "Runs the task without publishing the package",
})
def release_integration(ctx, target, dry_run=False):
    """
    Release to PyPI a specific check as it is on the repo HEAD
    """
    # sanity check on the target
    if target not in AGENT_BASED_INTEGRATIONS:
        raise Exit("Provided target is not an Agent-based Integration")

    # retrieve credentials
    username = os.environ.get('DD_PYPI_USERNAME')
    password = os.environ.get('DD_PYPI_PASSWORD')
    if not (username and password):
        raise Exit("Please set DD_PYPI_USERNAME and DD_PYPI_PASSWORD env vars and try again.")

    print("Building and publishing {} on PyPI".format(target))
    with ctx.cd(target):
        ctx.run('python setup.py bdist_wheel', hide='stdout')
        print("Build done, uploading the package...")
        if not dry_run:
            cmd = 'twine upload -u "{}" -p "{}" dist/*'.format(username, password)
            ctx.run(cmd, warn=True)

    print("Done.")


@task(help={
    'dest_path': "The path to the destination file, using stdout if empty"
})
def compile_requirements(ctx, dest_path=None):
    """
    Write the `agent_requirements.txt` file at the root of the repo listing
    all the agent based integrations pinned at the version they currently
    have in HEAD.
    """
    all_platforms = sorted(['linux', 'mac_os', 'windows'])

    entries = []
    for i in AGENT_BASED_INTEGRATIONS:
        if i in AGENT_V5_ONLY:
            print("Integration {} is only shipped with version 5 of the Agent, skip...")
            continue
        version = get_version_string(i)
        m = load_manifest(i)
        platforms = sorted(m.get('supported_os', []))
        # all platforms
        if platforms == all_platforms:
            entries.append('{}=={}'.format(i, version))
        # one specific platform
        elif len(platforms) == 1:
            entries.append("{}=={}; sys_platform == '{}'".format(i, version, platforms[0]))
        # assuming linux+mac here for brevity
        elif 'windows' not in platforms:
            entries.append("{}=={}; sys_platform != 'windows'".format(i, version))
        else:
            print("Can't parse the 'supported_os' list for the check {}: {}".format(i, platforms))

    output = '\n'.join(entries)

    if dest_path:
        with open(dest_path, 'w') as f:
            f.write(output)
    else:
        print(output)
