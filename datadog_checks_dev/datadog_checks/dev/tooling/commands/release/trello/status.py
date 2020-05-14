# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json

import click

from ....trello import TrelloClient
from ...console import CONTEXT_SETTINGS


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Gather statistics from the Trello release board')
@click.option('--json', '-j', 'as_json', is_flag=True, help='Return as raw JSON instead')
@click.pass_context
def status(ctx: click.Context, as_json: bool) -> None:
    """Print tabular status of Agent Release based on Trello columns.

    See trello subcommand for details on how to setup access:

    `ddev release trello -h`.
    """

    user_config = ctx.obj
    trello = TrelloClient(user_config)

    counts = trello.count_by_columns()

    row_format = '{:30} | {:<15} | {:<15} | {:<15} | {:<15} | {}'
    headers = ('Total', 'In Progress', 'Issues Found', 'Awaiting Build', 'Done')

    if as_json:
        print(json.dumps(counts, indent=2))
        return

    totals = dict(zip(headers, [0] * len(headers)))

    print(row_format.format('Team', *headers))
    print(row_format.format('--', *['--' for _ in headers]))
    for team, data in counts.items():
        for header in headers:
            totals[header] += data[header]
        row = row_format.format(team, *[data[header] for header in headers])
        print(row)

    print(row_format.format('--', *['--' for _ in headers]))
    row = row_format.format('TOTALS', *[totals[header] for header in headers])
    print(row)
