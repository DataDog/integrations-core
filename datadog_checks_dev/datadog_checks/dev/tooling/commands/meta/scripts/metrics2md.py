# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import csv
from io import StringIO

import click
import pyperclip

from ....utils import read_metric_data_file
from ...console import CONTEXT_SETTINGS, abort, echo_success

VALID_FIELDS = {
    'metric_name',
    'metric_type',
    'interval',
    'unit_name',
    'per_unit_name',
    'description',
    'orientation',
    'integration',
    'short_name',
}

DEFAULT_FIELDS = ('metric_name', 'description', 'metric_type', 'unit_name')


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Convert metadata.csv files to Markdown tables')
@click.argument('check')
@click.argument('fields', nargs=-1)
def metrics2md(check, fields):
    """Convert a check's metadata.csv file to a Markdown table, which will be copied to your clipboard.

    By default it will be compact and only contain the most useful fields. If you wish to use arbitrary
    metric data, you may set the check to `cb` to target the current contents of your clipboard.
    """
    if not fields:
        fields = DEFAULT_FIELDS
    else:
        chosen_fields = set(fields)
        if chosen_fields - VALID_FIELDS:
            abort(f"You must select only from the following fields: {', '.join(VALID_FIELDS)}")

        # Deduplicate and retain order
        old_fields = fields
        fields = []
        for field in old_fields:
            if field not in chosen_fields:
                continue

            fields.append(field)
            chosen_fields.discard(field)

    if check == 'cb':
        metric_data = pyperclip.paste()
    else:
        metric_data = read_metric_data_file(check)

    reader = csv.DictReader(StringIO(metric_data), delimiter=',')

    rows = []
    for csv_row in reader:
        rows.append(' | '.join(csv_row[field] or 'N/A' for field in fields))

    rows.sort()
    num_metrics = len(rows)

    md_table_rows = [' | '.join(fields), ' | '.join('---' for _ in fields)]
    md_table_rows.extend(rows)

    pyperclip.copy('\n'.join(md_table_rows))
    echo_success(f"Successfully copied table with {num_metrics} metric{'s' if num_metrics > 1 else ''}")
