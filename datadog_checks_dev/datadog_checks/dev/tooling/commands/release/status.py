# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ...trello import TrelloClient
from ..console import CONTEXT_SETTINGS


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Gather statistics from the Trello release board')
@click.option('--json', '-j', 'as_json', is_flag=True, help='Return as raw JSON instead')
@click.pass_context
def status(ctx: click.Context, as_json: bool) -> None:
    """Print tabular status of Agent Release based on Trello columns.


    \b
    To use Trello:
    1. Go to `https://trello.com/app-key` and copy your API key.
    2. Run `ddev config set trello.key` and paste your API key.
    3. Go to `https://trello.com/1/authorize?key=key&name=name&scope=read,write&expiration=never&response_type=token`,
       where `key` is your API key and `name` is the name to give your token, e.g. ReleaseTestingYourName.
       Authorize access and copy your token.
    4. Run `ddev config set trello.token` and paste your token.
    """
    user_config = ctx.obj
    trello = TrelloClient(user_config)

    counts = trello.count_by_columns()

    row_format = '{:30} | {:<15} | {:<15} | {:<15} | {:<15} | {}'
    headers = ('Total', 'In Progress', 'Issues Found', 'Awaiting Build', 'Done')

    if as_json:
        print(counts)
        return

    print(row_format.format('Team', *headers))
    for team, data in counts.items():
        row = row_format.format(team, *[data[header] for header in headers])
        print(row)
