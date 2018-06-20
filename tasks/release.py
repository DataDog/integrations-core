# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals
import os
import sys

from packaging import version
from invoke import task
from invoke.exceptions import Exit
from colorama import Fore

from .constants import AGENT_BASED_INTEGRATIONS, AGENT_V5_ONLY, ROOT, AGENT_REQ_FILE
from .utils.git import (
    get_current_branch, parse_pr_numbers, get_diff, git_tag, git_commit
)
from .utils.common import (
    get_version_string, get_release_tag_string, update_version_module
)
from .utils.github import get_changelog_types, get_pr
from .utils.requirements import get_requirement_line, update_requirements
from .changelog import do_update_changelog, CHANGELOG_TYPE_NONE


@task(help={
    'target': "The check to tag",
    'version': "The desired version, defaults to the one from setup.py",
    'dry-run': "Runs the task without actually doing anything",
})
def release_tag(ctx, target, version=None, dry_run=False, push=True):
    """
    Tag the HEAD of the git repo with the current release number for a
    specific check. The tag is pushed to origin by default.

    Notice: specifying a different version than the one in setup.py is
    a maintainance task that should be run under very specific circumstances
    (e.g. re-align an old release performed on the wrong commit).
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
        git_tag(ctx, tag, push)
    except Exception as e:
        print(e)


@task
def print_shippable(ctx, quiet=False):
    """
    Print all the checks that can be released.
    """
    for target in AGENT_BASED_INTEGRATIONS:
        # get the name of the current release tag
        cur_version = get_version_string(target)
        target_tag = get_release_tag_string(target, cur_version)

        # get the diff from HEAD
        diff_lines = get_diff(ctx, target, target_tag)

        # get the number of PRs that could be potentially released
        # Only show the ones that have a changelog label that isn't no-changelog
        pr_numbers = parse_pr_numbers(diff_lines)
        all_no_changelog = True
        for pr_num in pr_numbers:
            try:
                payload = get_pr(pr_num)
                changelog_labels = get_changelog_types(payload)

                if not changelog_labels:
                    msg = Fore.RED + "PR #{} has no changelog label attached, please add one!\n".format(pr_num)
                    sys.stderr.write(msg)
                    continue

                if changelog_labels[0] != CHANGELOG_TYPE_NONE:
                    all_no_changelog = False
            except Exception as e:
                sys.stderr.write("Unable to fetch info for PR #{}: {}\n".format(pr_num, e))
                continue

        if pr_numbers and not all_no_changelog:
            if quiet:
                print(target)
            else:
                print("Check {} has {} merged PRs that could be released".format(target, len(pr_numbers)))


@task(help={
    'target': "List the pending changes for the target check.",
})
def release_show_pending(ctx, target):
    """
    Print all the pending PRs for a given check.

    Example invocation:
        inv release-show-pending mysql
    """
    # sanity check on the target
    if target not in AGENT_BASED_INTEGRATIONS:
        raise Exit("Provided target is not an Agent-based Integration")

    # get the name of the current release tag
    cur_version = get_version_string(target)
    target_tag = get_release_tag_string(target, cur_version)

    # get the diff from HEAD
    diff_lines = get_diff(ctx, target, target_tag)

    # for each PR get the title, we'll use it to populate the changelog
    pr_numbers = parse_pr_numbers(diff_lines)
    print("Found {} PRs merged since tag: {}".format(len(pr_numbers), target_tag))
    for pr_num in pr_numbers:
        try:
            payload = get_pr(pr_num)
        except Exception as e:
            sys.stderr.write("Unable to fetch info for PR #{}\n: {}".format(pr_num, e))
            continue

        changelog_types = get_changelog_types(payload)
        if not changelog_types:
            changelog_status = Fore.RED + 'WARNING! No changelog labels attached.'
        elif len(changelog_types) > 1:
            changelog_status = Fore.RED + 'WARNING! Too many changelog labels attached: {}'.format(','.join(changelog_types))
        else:
            changelog_status = Fore.GREEN + changelog_types[0]

        print(payload.get('title'))
        print(" * Url: {}".format(payload.get('html_url')))
        print(" * Changelog status: {}".format(changelog_status))
        print("")


@task(help={
    'target': "The check to release",
    'new_version': "The new version",
})
def release_prepare(ctx, target, new_version):
    """
    Perform a set of operations needed to release a single check:

     * update the version in __about__.py
     * update the changelog
     * update the AGENT_REQ_FILE file
     * commit the above changes

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

    # update the global requirements file
    req_file = os.path.join(ROOT, AGENT_REQ_FILE)
    print("Updating the requirements file {}".format(req_file))
    update_requirements(req_file, target, get_requirement_line(target, new_version))

    # commit the changes
    msg = "Bumped {} version to {}".format(target, new_version)
    git_commit(ctx, [target, AGENT_REQ_FILE], msg)

    # done
    print("All done, remember to push to origin and open a PR to merge these changes on master")


@task(help={
    'target': "The check to release",
    'dry-run': "Runs the task without publishing the package",
})
def release_upload(ctx, target, dry_run=False):
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
    entries = []
    for i in AGENT_BASED_INTEGRATIONS:
        if i in AGENT_V5_ONLY:
            print("Integration {} is only shipped with version 5 of the Agent, skip...")
            continue

        try:
            version = get_version_string(i)
            entries.append(get_requirement_line(i, version))
        except Exception as e:
            print(Fore.RED + "Error generating line: {}".format(e))
            continue

    output = '\n'.join(sorted(entries))  # sorting in case AGENT_BASED_INTEGRATIONS is out of order

    if dest_path:
        with open(dest_path, 'w') as f:
            f.write(output)
    else:
        print(output)
