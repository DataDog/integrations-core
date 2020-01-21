# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ....constants import CHANGELOG_TYPE_NONE
from ....git import get_commits_since
from ....github import get_changelog_types, get_pr, parse_pr_numbers
from ....release import get_release_tag_string
from ....utils import get_valid_checks, get_version_string
from ...console import CONTEXT_SETTINGS, echo_failure, echo_info, echo_warning


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Show all the checks that can be released.')
@click.option('--quiet', '-q', is_flag=True)
@click.pass_context
def ready(ctx, quiet):
    """Show all the checks that can be released."""
    user_config = ctx.obj
    cached_prs = {}

    for target in sorted(get_valid_checks()):
        # get the name of the current release tag
        cur_version = get_version_string(target)
        target_tag = get_release_tag_string(target, cur_version)

        # get the diff from HEAD
        diff_lines = get_commits_since(target, target_tag)

        # get the number of PRs that could be potentially released
        # Only show the ones that have a changelog label that isn't no-changelog
        pr_numbers = parse_pr_numbers(diff_lines)

        shippable_prs = 0
        for pr_num in pr_numbers:
            try:
                if pr_num in cached_prs:
                    changelog_labels = cached_prs[pr_num]
                    if len(changelog_labels) != 1:
                        continue
                else:
                    payload = get_pr(pr_num, user_config)
                    changelog_labels = get_changelog_types(payload)
                    cached_prs[pr_num] = changelog_labels

                    if not changelog_labels:
                        echo_warning(f'PR #{pr_num} has no changelog label attached, please add one! Skipping...')
                        continue

                    if len(changelog_labels) > 1:
                        echo_warning(
                            'Multiple changelog labels found attached to PR #{}, '
                            'please only use one! Skipping...'.format(pr_num)
                        )
                        continue

                if changelog_labels[0] != CHANGELOG_TYPE_NONE:
                    shippable_prs += 1
            except Exception as e:
                echo_failure(f'Unable to fetch info for PR #{pr_num}: {e}')
                continue

        if shippable_prs:
            if quiet:
                msg = target
            else:
                msg = 'Check {} has {} out of {} merged PRs that could be released' ''.format(
                    target, shippable_prs, len(pr_numbers)
                )
            echo_info(msg)
