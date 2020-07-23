# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click
import requests

from ...console import CONTEXT_SETTINGS, abort, echo_success


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Lookup Github username by email.')
@click.argument('email')
def email2ghuser(email):
    """Given an email, attempt to find a Github username
       associated with the email.

    `$ ddev meta scripts email2ghuser example@datadoghq.com`
    """

    try:
        response = requests.get(f'https://api.github.com/search/users?q={email}')
        response.raise_for_status()
        content = response.json()

        if content.get('total_count') == 0:
            abort(f'No username found for email {email}')

        user = content.get('items')[0]
        username = user.get('login')

        echo_success(f'Found username "{username}" associated with email {email}')

    except Exception as e:
        abort(str(e))
