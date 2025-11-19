import copy

import click

DESCRIPTION_SEED = """\
This monitor will alert you on XXX...

- Define the problem stated by the title.
- Answer why this is an issue worth alerting on.
- Describe the impact of the problem.

Official guidelines:
https://docs.datadoghq.com/developers/integrations/create-an-integration-recommended-monitor/#description
"""


@click.group
def monitor():
    """
    Work with monitors.
    """


def _edit(text):
    edited = click.edit(text=text, require_save=False)
    return "" if edited is None else edited


def _drop_fields(exported):
    x = copy.deepcopy(exported)
    x.pop('id', None)
    x['options'].pop('on_missing_data', None)
    return x


@monitor.command
@click.argument("export_json", type=click.File())
def create(export_json):
    """
    Create monitor spec from the JSON export of the monitor in the UI.

    The exported monitor cannot be committed as-is, we have to rename, add, and drop some fields.

    After you've copied the JSON in the UI you can either save it as a file or pipe it to STDIN:

    \b
    pbpaste | ddev meta monitor create -
    """
    import json
    from datetime import date

    exported = json.load(export_json)
    today = date.today().isoformat()
    wrangled = {
        "version": 2,
        "created_at": today,
        "last_updated_at": today,
        "title": _edit(text=exported["name"]).strip(),
        "description": _edit(text=DESCRIPTION_SEED).strip(),
        "tags": exported["tags"],
        "definition": _drop_fields(exported),
    }
    click.echo(
        json.dumps(
            wrangled,
            indent=2,
        )
    )
