# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
import requests

from ...console import CONTEXT_SETTINGS, abort, echo_success


@click.command(
    'remove-labels', context_settings=CONTEXT_SETTINGS, short_help='Remove all labels from an issue or pull request'
)
@click.argument('issue_number')
@click.pass_context
def remove_labels(ctx, issue_number):
    """Remove all labels from an issue or pull request. This is useful when there are too
    many labels and its state cannot be modified (known GitHub issue).

    \b
    `$ ddev meta scripts remove-labels 5626`
    """
    repo = ctx.obj['repo_name']
    github_config = ctx.obj['github']

    github_user = github_config.get('user')
    if not github_user:
        abort('No `github.user` has been set')

    github_token = github_config.get('token')
    if not github_token:
        abort('No `github.token` has been set')

    try:
        response = requests.delete(
            f'https://api.github.com/repos/DataDog/{repo}/issues/{issue_number}/labels',
            auth=(github_user, github_token),
        )
        response.raise_for_status()
    except Exception as e:
        abort(str(e))

    echo_success('Success!')
