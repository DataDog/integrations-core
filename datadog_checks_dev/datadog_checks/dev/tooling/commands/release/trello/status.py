# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from typing import List

import click
import pyperclip

from ....trello import TrelloClient
from ...console import CONTEXT_SETTINGS, echo_info, echo_success

ROW_FORMAT = {
    'verbose': '{:19} | {:<8} | {:<8} | {:<8} | {:<8} | {:<8} | {}',
    'summarized': '{:20} {:>4}',
}

HEADERS = {
    'verbose': ('Total', 'Inbox', 'In Progress', 'Issues Found', 'Awaiting Build', 'Done'),
    'summarized': ('Team', 'Done'),
}


ROW_DIVIDER = '-' * 4


def _get_percent(completed: int, assigned: int) -> int:
    return round((float(completed) / float(assigned)) * 100)


def _verbose_status(counts: dict, as_json: bool) -> List[str]:
    """Returns the Trello status output as a detailed table"""

    row_format = ROW_FORMAT['verbose']
    headers = HEADERS['verbose']

    if as_json:
        return [json.dumps(counts, indent=2)]

    totals = dict(zip(headers, [0] * len(headers)))

    output = []
    output.append(row_format.format('', '', '', 'In', 'Issues', 'Awaiting', ''))
    output.append(row_format.format('Team', 'Total', 'Inbox', 'Progress', 'Found', 'Build', 'Done'))
    output.append(row_format.format(ROW_DIVIDER, *[ROW_DIVIDER for _ in headers]))

    for team, data in counts.items():
        for header in headers:
            totals[header] += data[header]
        row = row_format.format(team, *[data[header] for header in headers])
        output.append(row)

    output.append(row_format.format(ROW_DIVIDER, *[ROW_DIVIDER for _ in headers]))
    row = row_format.format('TOTALS', *[totals[header] for header in headers])
    output.append(row)

    return output


def _summary_status(counts: dict, as_json: bool) -> List[str]:
    """Returns the Trello status output as a summarized table"""

    row_format = ROW_FORMAT['summarized']

    total_assigned = 0
    total_completed = 0

    computed_data = []
    for team_name, data in counts.items():
        completed = data['Done']
        assigned = data['Total']

        total_completed += completed
        total_assigned += assigned

        if assigned == 0:
            computed_data.append((team_name, 100))
            continue

        computed_data.append((team_name, _get_percent(completed, assigned)))

    computed_data.sort(key=lambda x: x[1])
    total_percent_complete = _get_percent(total_completed, total_assigned)

    if as_json:
        json_data = {}
        for team_name, pct_complete in computed_data:
            json_data[team_name] = {
                "PctComplete": pct_complete,
            }

        json_data['Total'] = {
            "PctComplete": total_percent_complete,
        }

        return [json.dumps(json_data, indent=2)]

    output = []
    output.append(row_format.format(*HEADERS['summarized']))
    output.append(row_format.format(ROW_DIVIDER * 5, ROW_DIVIDER))

    for team_name, pct_complete in computed_data:
        row = row_format.format(team_name, "{}%".format(pct_complete))
        output.append(row)

    output.append(row_format.format(ROW_DIVIDER * 5, ROW_DIVIDER))
    output.append(row_format.format('TOTAL', "{}%".format(total_percent_complete)))

    return output


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Gather statistics from the Trello release board')
@click.option('--verbose', '-v', is_flag=True, help='Return the detailed results instead of the aggregates')
@click.option('--json', '-j', 'as_json', is_flag=True, help='Return as raw JSON instead')
@click.option('--clipboard', '-c', is_flag=True, help='Copy output to clipboard')
@click.pass_context
def status(ctx: click.Context, verbose: bool, as_json: bool, clipboard: bool) -> None:
    """Print tabular status of Agent Release based on Trello columns.

    See trello subcommand for details on how to setup access:

    `ddev release trello -h`.
    """

    user_config = ctx.obj
    trello = TrelloClient(user_config)

    counts = trello.count_by_columns()

    if not verbose:
        output = _summary_status(counts, as_json)
    else:
        output = _verbose_status(counts, as_json)

    out = '\n'.join(output)

    msg = '\nTrello Status Report:\n'
    if clipboard:
        try:
            pyperclip.copy(out)
            msg = '\nTrello Status Report (copied to your clipboard):\n'
        except Exception:
            pass

    echo_success(msg)
    echo_info(out)
