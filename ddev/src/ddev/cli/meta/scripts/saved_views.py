# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import webbrowser
from urllib.parse import parse_qs, urlparse

import click

TIP = """
We're about to open JSON definition of the saved view in your browser. Copy the JSON on that page and paste at
the prompt. Hit any key to continue.
"""


def _convert_options(api_options):
    stream = api_options["stream"]
    asset_options = {
        "columns": stream["columns"],
    }
    for old_f, new_f in {
        "showDateColumn": "show_date_column",
        "showMessageColumn": "show_message_column",
        "messageDisplay": "message_display",
        "showTimeline": "show_timeline",
    }.items():
        if old_f in stream:
            asset_options[new_f] = stream[old_f]

    return asset_options


def convert_to_asset(sv_json):
    """
    Take saved view json from the API and convert it to an asset definition.
    """
    asset_def = {}
    logs_view = sv_json["logs_view"]

    keep_as_is = (
        "name",
        "type",
        "page",
    )
    for f in keep_as_is:
        asset_def[f] = logs_view[f]

    renames = {"search": "query", "facets": "visible_facets"}
    for old_f, new_f in renames.items():
        asset_def[new_f] = logs_view[old_f]
    asset_def["options"] = _convert_options(logs_view["options"])
    asset_def["timerange"] = {"interval_ms": logs_view["timerange"]["interval"]}
    return asset_def


@click.command()
@click.argument('saved_view_permalink', type=str)
def sv(saved_view_permalink):
    """
    Helper for working with Logs Saved Views.

    Accepts a permalink to a saved view, then guides you towards creating an asset definition in JSON.

    VERY EARLY VERSION, MAKE SURE TO CHECK --help FOR CHANGES BEFORE USING.
    """
    parsed_url = urlparse(saved_view_permalink)
    # urllib parses query values as lists, so we must take the first (and only) element as the ID.
    sv_id = parse_qs(parsed_url.query)['saved-view-id'][0]
    json_url = parsed_url._replace(path=f"/api/v1/logs/views/{sv_id}", query='').geturl()
    input(TIP)
    webbrowser.open(json_url)
    sv_json = json.loads(click.prompt(text="Paste your JSON here, then hit ENTER ", prompt_suffix="> "))

    click.echo(json.dumps(convert_to_asset(sv_json), indent=2, sort_keys=True))
