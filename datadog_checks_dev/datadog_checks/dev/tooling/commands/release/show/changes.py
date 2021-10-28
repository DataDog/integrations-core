# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ....git import get_commits_since
from ....github import get_changelog_types, get_pr, parse_pr_numbers
from ....release import get_release_tag_string
from ....utils import complete_valid_checks, get_valid_checks, get_version_string
from ...console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning, validate_check_arg


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Show all the pending PRs for a given check.')
@click.argument('check', autocompletion=complete_valid_checks, callback=validate_check_arg)
@click.option('--organization', '-r', default='DataDog', help="The Github organization the repository belongs to")
@click.option(
    '--tag-pattern',
    default=None,
    help="The regex pattern for the format of the tag. Required if the tag doesn't follow semver",
)
@click.option(
    '--tag-prefix', default=None, help="Specify the prefix of the tag to use if the tag doesn't follow semver"
)
@click.option('--dry-run', '-n', is_flag=True, help="Run the command in dry-run mode")
@click.option(
    '--since', default=None, help="The git ref to use instead of auto-detecting the tag to view changes since"
)
@click.option('--exclude-branch', default=None, help="Exclude changes comming from a specific branch")
@click.pass_context
def changes(ctx, check, tag_pattern, tag_prefix, dry_run, organization, since, exclude_branch):
    """Show all the pending PRs for a given check."""
    if not dry_run and check and check not in get_valid_checks():
        abort(f'Check `{check}` is not an Agent-based Integration')

    # get the name of the current release tag
    cur_version = since or get_version_string(check, pattern=tag_pattern, tag_prefix=tag_prefix)
    if not cur_version:
        abort(
            'Failed to retrieve the latest version. Please ensure your project or check has a proper set of tags '
            'following SemVer and matches the provided tag_prefix and/or tag_pattern.'
        )
    target_tag = get_release_tag_string(check, cur_version)

    # get the diff from HEAD
    diff_lines = get_commits_since(check, target_tag, exclude_branch=exclude_branch)

    # for each PR get the title, we'll use it to populate the changelog
    pr_numbers = parse_pr_numbers(diff_lines)
    if not dry_run:
        echo_info(f'Found {len(pr_numbers)} PRs merged since tag: {target_tag}')

    user_config = ctx.obj
    if dry_run:
        changelog_types = []

        for pr_num in pr_numbers:
            try:
                payload = get_pr(pr_num, user_config, org=organization)
            except Exception as e:
                echo_failure(f'Unable to fetch info for PR #{pr_num}: {e}')
                continue
            current_changelog_types = get_changelog_types(payload)
            if not current_changelog_types:
                abort(f'No valid changelog labels found attached to PR #{pr_num}, please add one!')
            elif len(current_changelog_types) > 1:
                abort(f'Multiple changelog labels found attached to PR #{pr_num}, please only use one!')

            current_changelog_type = current_changelog_types[0]
            if current_changelog_type != 'no-changelog':
                changelog_types.append(current_changelog_type)

        return cur_version, changelog_types
    else:
        for pr_num in pr_numbers:
            try:
                payload = get_pr(pr_num, user_config, org=organization)
            except Exception as e:
                echo_failure(f'Unable to fetch info for PR #{pr_num}: {e}')
                continue

            changelog_types = get_changelog_types(payload)

            echo_success(payload.get('title'))
            echo_info(f" * Url: {payload.get('html_url')}")

            echo_info(' * Changelog status: ', nl=False)
            if not changelog_types:
                echo_warning('WARNING! No changelog labels attached.\n')
            elif len(changelog_types) > 1:
                echo_warning(f"WARNING! Too many changelog labels attached: {', '.join(changelog_types)}\n")
            else:
                echo_success(f'{changelog_types[0]}\n')
