# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import re

import click
import requests

from ....utils import ensure_dir_exists, path_join, write_file
from ...constants import get_root
from ...utils import get_valid_integrations, load_manifest, write_manifest
from ..console import CONTEXT_SETTINGS, abort

BOARD_ID_PATTERN = r'{site}/[^/]+/([^/]+)/.+'
SCREEN_API = 'https://api.{site}/api/v1/screen/{board_id}'


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Dashboard utilities')
def dash():
    pass


@dash.command(context_settings=CONTEXT_SETTINGS, short_help='Export a Dashboard as JSON')
@click.argument('url')
@click.argument('integration', required=False)
@click.pass_context
def export(ctx, url, integration):
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
            SCREEN_API.format(site=site, board_id=board_id), params={'api_key': api_key, 'application_key': app_key}
        )
        response.raise_for_status()
    except Exception as e:
        abort(str(e).replace(api_key, '*' * len(api_key)).replace(app_key, '*' * len(app_key)))

    payload = response.json()
    payload.setdefault('author_info', {})
    payload['author_info']['author_name'] = 'Datadog'
    payload.setdefault('created_by', {})
    payload['created_by']['email'] = 'support@datadoghq.com'
    payload['created_by']['handle'] = 'support@datadoghq.com'
    payload['created_by']['name'] = 'Datadog'
    payload['created_by'].pop('icon', None)
    output = json.dumps(payload, indent=4, sort_keys=True)

    file_name = payload['board_title'].strip().lower()
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
            new_file_name = file_name.replace(match, '', 1).strip()
            if new_file_name:
                file_name = new_file_name

        file_name = f"{file_name.replace(' ', '_')}.json"
        location = path_join(get_root(), integration, 'assets', 'dashboards')
        ensure_dir_exists(location)

        manifest['assets']['dashboards'][payload['board_title']] = f'assets/dashboards/{file_name}'
        write_manifest(manifest, integration)
    else:
        file_name = f"{file_name.replace(' ', '_')}.json"
        location = os.getcwd()

    file_path = path_join(location, file_name)
    write_file(file_path, output)
