# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import re

import click
import requests

from ....fs import ensure_dir_exists, path_join, write_file
from ...constants import get_root
from ...utils import get_valid_integrations, load_manifest, write_manifest
from ..console import CONTEXT_SETTINGS, abort, echo_success

BOARD_ID_PATTERN = r'{site}/[^/]+/([^/]+)'
DASHBOARD_API = 'https://api.{site}/api/v1/dashboard/{board_id}'
REQUIRED_FIELDS = ["layout_type", "title", "description", "template_variables", "widgets"]


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Dashboard utilities')
def dash():
    pass


@dash.command(context_settings=CONTEXT_SETTINGS, short_help='Export a Dashboard as JSON')
@click.argument('url')
@click.argument('integration', required=True)
@click.option(
    '--author',
    '-a',
    required=False,
    default='Datadog',
    help="The owner of this integration's dashboard. Default is 'Datadog'",
)
@click.pass_context
def export(ctx, url, integration, author):
    if integration and integration not in get_valid_integrations():
        abort(f'Unknown integration `{integration}`')

    org = ctx.obj['org']
    if not org:
        abort('No `org` has been set')

    if org not in ctx.obj['orgs']:
        abort(f'Selected org {org} is not in `orgs`')

    org = ctx.obj['orgs'][org]

    api_key = org.get('api_key')
    if not api_key:
        abort(f'No `api_key` has been set for org `{org}`')

    app_key = org.get('app_key')
    if not app_key:
        abort(f'No `app_key` has been set for org `{org}`')

    site = org.get('site')
    if not site:
        abort(f'No `site` has been set for org `{org}`')

    match = re.search(BOARD_ID_PATTERN.format(site=re.escape(site)), url)
    if match:
        board_id = match.group(1)
    else:
        abort('Invalid `url`')

    try:
        response = requests.get(
            DASHBOARD_API.format(site=site, board_id=board_id), params={'api_key': api_key, 'application_key': app_key}
        )
        response.raise_for_status()
    except Exception as e:
        abort(str(e).replace(api_key, '*' * len(api_key)).replace(app_key, '*' * len(app_key)))

    payload = response.json()
    new_payload = {field: payload[field] for field in REQUIRED_FIELDS}
    new_payload['author_name'] = author

    output = json.dumps(new_payload, indent=4, sort_keys=True)

    file_name = new_payload['title'].strip().lower()
    if integration:
        manifest = load_manifest(integration)

        match = ''
        if file_name.startswith(integration):
            match = integration
        else:
            display_name = manifest['display_name'].lower()
            if file_name.startswith(display_name):
                match = display_name

        if match:
            new_file_name = file_name.replace(match, '', 1).strip(" -")
            if new_file_name:
                file_name = new_file_name

        file_name = f"{file_name.replace(' ', '_')}.json"
        location = path_join(get_root(), integration, 'assets', 'dashboards')
        ensure_dir_exists(location)

        manifest['assets']['dashboards'][new_payload['title']] = f'assets/dashboards/{file_name}'
        write_manifest(manifest, integration)
    else:
        file_name = f"{file_name.replace(' ', '_')}.json"
        location = os.getcwd()

    file_path = path_join(location, file_name)
    write_file(file_path, output)
    echo_success(f"Successfully wrote dashboard: `{file_name}` for integration: `{integration}`")
