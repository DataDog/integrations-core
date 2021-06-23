# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...git import git_tag, git_tag_list
from ...release import get_release_tag_string
from ...utils import complete_valid_checks, get_valid_checks, get_version_string
from ..console import CONTEXT_SETTINGS, abort, echo_info, echo_success, echo_waiting, echo_warning


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Tag the git repo with the current release of a check')
@click.argument('check', autocompletion=complete_valid_checks)
@click.argument('version', required=False)
@click.option('--push/--no-push', default=True)
@click.option('--dry-run', '-n', is_flag=True)
def tag(check, version, push, dry_run):
    """Tag the HEAD of the git repo with the current release number for a
    specific check. The tag is pushed to origin by default.

    You can tag everything at once by setting the check to `all`.

    Notice: specifying a different version than the one in `__about__.py` is
    a maintenance task that should be run under very specific circumstances
    (e.g. re-align an old release performed on the wrong commit).
    """
    tagging_all = check == 'all'

    valid_checks = get_valid_checks()
    if not tagging_all and check not in valid_checks:
        abort(f'Check `{check}` is not an Agent-based Integration')

    if tagging_all:
        if version:
            abort('You cannot tag every check with the same version')
        checks = sorted(valid_checks)
    else:
        checks = [check]

    # Check for any new tags
    tagged = False
    existing_tags = git_tag_list()

    for check in checks:
        echo_info(f'{check}:')

        # get the current version
        if not version:
            version = get_version_string(check)

        # get the tag name
        release_tag = get_release_tag_string(check, version)
        echo_waiting(f'Tagging HEAD with {release_tag}... ', indent=True, nl=False)

        if dry_run:
            # Get latest tag for check
            if release_tag in existing_tags:
                echo_warning('already exists (dry-run)')
            else:
                tagged = True
                echo_success("success! (dry-run)")
            version = None
            continue

        result = git_tag(release_tag, push)

        if result.code == 128 or 'already exists' in result.stderr:
            echo_warning('already exists')
        elif result.code != 0:
            abort(f'\n{result.stdout}{result.stderr}', code=result.code)
        else:
            tagged = True
            echo_success('success!')

        # Reset version
        version = None

    if not tagged:
        abort(code=2)
