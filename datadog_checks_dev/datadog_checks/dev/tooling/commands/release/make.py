# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from contextlib import suppress

import click
from semver import finalize_version, parse_version_info

from ...constants import BETA_PACKAGES, NOT_CHECKS, VERSION_BUMP, get_agent_release_requirements
from ...git import get_current_branch, git_commit
from ...release import get_agent_requirement_line, update_agent_requirements, update_version_module
from ...utils import complete_valid_checks, get_bump_function, get_valid_checks, get_version_string
from ..console import CONTEXT_SETTINGS, abort, echo_info, echo_success, echo_waiting, echo_warning
from . import changelog
from .show import changes


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Release one or more checks')
@click.argument('checks', autocompletion=complete_valid_checks, nargs=-1, required=True)
@click.option('--version')
@click.option('--new', 'initial_release', is_flag=True, help='Ensure versions are at 1.0.0')
@click.option('--skip-sign', is_flag=True, help='Skip the signing of release metadata')
@click.option('--sign-only', is_flag=True, help='Only sign release metadata')
@click.option('--exclude', help='Comma-separated list of checks to skip')
@click.pass_context
def make(ctx, checks, version, initial_release, skip_sign, sign_only, exclude):
    """Perform a set of operations needed to release checks:

    \b
      * update the version in `__about__.py`
      * update the changelog
      * update the `requirements-agent-release.txt` file
      * update in-toto metadata
      * commit the above changes

    You can release everything at once by setting the check to `all`.

    \b
    If you run into issues signing:
    \b
      - Ensure you did `gpg --import <YOUR_KEY_ID>.gpg.pub`
    """
    # Import lazily since in-toto runs a subprocess to check for gpg2 on load
    from ...signing import update_link_metadata, YubikeyException

    releasing_all = 'all' in checks

    valid_checks = get_valid_checks()
    if not releasing_all:
        for check in checks:
            if check not in valid_checks:
                abort(f'Check `{check}` is not an Agent-based Integration')

    # don't run the task on the master branch
    if get_current_branch() == 'master':
        abort('Please create a release branch, you do not want to commit to master directly.')

    if releasing_all:
        if version:
            abort('You cannot bump every check to the same version')
        checks = sorted(valid_checks)
    else:
        checks = sorted(checks)

    if exclude:
        for check in exclude.split(','):
            with suppress(ValueError):
                checks.remove(check)

    if initial_release:
        version = '1.0.0'

    # Keep track of the list of checks that have been updated.
    updated_checks = []
    for check in checks:
        if sign_only:
            updated_checks.append(check)
            continue
        elif initial_release and check in BETA_PACKAGES:
            continue

        # Initial releases will only bump if not already 1.0.0 so no need to always output
        if not initial_release:
            echo_success(f'Check `{check}`')

        if version:
            # sanity check on the version provided
            cur_version = get_version_string(check)

            if version == 'final':
                # Remove any pre-release metadata
                version = finalize_version(cur_version)
            else:
                # Keep track of intermediate version bumps
                prev_version = cur_version
                for method in version.split(','):
                    # Apply any supported version bumping methods. Chaining is required for going
                    # from mainline releases to development releases since e.g. x.y.z > x.y.z-rc.A.
                    # So for an initial bug fix dev release you can do `fix,rc`.
                    if method in VERSION_BUMP:
                        version = VERSION_BUMP[method](prev_version)
                        prev_version = version

            p_version = parse_version_info(version)
            p_current = parse_version_info(cur_version)
            if p_version <= p_current:
                if initial_release:
                    continue
                else:
                    abort(f'Current version is {cur_version}, cannot bump to {version}')
        else:
            cur_version, changelog_types = ctx.invoke(changes, check=check, dry_run=True)
            if not changelog_types:
                echo_warning(f'No changes for {check}, skipping...')
                continue
            bump_function = get_bump_function(changelog_types)
            version = bump_function(cur_version)

        if initial_release:
            echo_success(f'Check `{check}`')

        # update the version number
        echo_info(f'Current version of check {check}: {cur_version}')
        echo_waiting(f'Bumping to {version}... ', nl=False)
        update_version_module(check, cur_version, version)
        echo_success('success!')

        # update the CHANGELOG
        echo_waiting('Updating the changelog... ', nl=False)
        # TODO: Avoid double GitHub API calls when bumping all checks at once
        ctx.invoke(
            changelog,
            check=check,
            version=version,
            old_version=cur_version,
            initial=initial_release,
            quiet=True,
            dry_run=False,
        )
        echo_success('success!')

        commit_targets = [check]
        updated_checks.append(check)
        # update the list of integrations to be shipped with the Agent
        if check not in NOT_CHECKS:
            req_file = get_agent_release_requirements()
            commit_targets.append(os.path.basename(req_file))
            echo_waiting('Updating the Agent requirements file... ', nl=False)
            update_agent_requirements(req_file, check, get_agent_requirement_line(check, version))
            echo_success('success!')

        echo_waiting('Committing files...')

        # commit the changes.
        # do not use [ci skip] so releases get built https://docs.gitlab.com/ee/ci/yaml/#skipping-jobs
        msg = f'[Release] Bumped {check} version to {version}'
        git_commit(commit_targets, msg, update=True)

        if not initial_release:
            # Reset version
            version = None

    if sign_only or not skip_sign:
        if not updated_checks:
            abort('There are no new checks to sign and release!')
        echo_waiting('Updating release metadata...')
        echo_info('Please touch your Yubikey immediately after entering your PIN!')
        try:
            commit_targets = update_link_metadata(updated_checks)
            git_commit(commit_targets, '[Release] Update metadata', force=True)
        except YubikeyException as e:
            abort(f'A problem occurred while signing metadata: {e}')

    # done
    echo_success('All done, remember to push to origin and open a PR to merge these changes on master')
